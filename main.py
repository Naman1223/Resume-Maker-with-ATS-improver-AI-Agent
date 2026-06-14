from pydantic import Field
import os
import re
import pydantic as pd
import subprocess
from typing import TypedDict
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.graph import StateGraph, START, END
from conversions import Conversion

load_dotenv()


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) that LLMs often add."""
    return re.sub(r"^```(?:json)?\s*\n?|\n?```\s*$", "", text.strip()).strip()

class SchemaFeedback(pd.BaseModel):
    ats_score: int = Field(description="ATS score ranging from 0-100")
    improvements: list[dict] = Field(description="List of improvements in the Resume and the suggestion to improve it")

class AgentState(TypedDict):
    file_path: str
    resume_md: str
    job_description: str
    improved_resume: str
    resume_latex: str
    ats_score: int


def md(state: AgentState):
    file_path = state["file_path"]
    state["resume_md"] = Conversion(file_path).to_md()
    return state


def analyze_and_improve(state: AgentState) -> AgentState:
    """Score the resume and rewrite it in a single node — the resume is read from
    state once and reused for both LLM calls without being stored twice."""

    resume_md       = state.get("resume_md", "")
    job_description = state.get("job_description", "")

    # ── Shared LLM (scoring is deterministic; rewrite allows some creativity) ──
    llm = ChatNVIDIA(
        model=os.getenv("MODEL"),
        api_key=os.getenv("NVIDIA_API_KEY"),
        temperature=0,
        max_completion_tokens=4000,
        top_p=1,
    )
    structured_llm = llm.with_structured_output(SchemaFeedback)

    # ── Step 1: Score & audit ──
    FEEDBACK_PROMPT = """
        You are a senior ATS expert and professional resume coach.

        Evaluate the resume below and return a structured JSON response with exactly two top-level keys:

        1. "ats_score" — An integer from 0 to 100 representing ATS performance.
           Score each category separately, then sum:
            - Keywords match (job description alignment): 30 pts
            - Measurable achievements: 20 pts
            - Standard section headings: 15 pts
            - ATS-safe formatting (no tables/columns/graphics): 15 pts
            - Action verbs: 10 pts
            - Contact info completeness: 5 pts
            - Grammar/spelling: 5 pts

        2. "improvements" — A list of improvement objects. Each must have:
            - "category": one of ["Keywords", "Formatting", "Impact", "Structure", "Skills", "Contact", "Grammar", "ATS Compatibility"]
            - "priority": one of ["High", "Medium", "Low"]
            - "issue": a short description of the specific problem found
            - "suggestion": a concrete, actionable fix the candidate should apply

        Return ONLY valid JSON. No markdown fences, no explanations outside the JSON.

        --- RESUME START ---
        {resume_md}
        --- RESUME END ---

        --- JOB DESCRIPTION START ---
        {job_description}
        --- JOB DESCRIPTION END ---
    """

    audit: SchemaFeedback = structured_llm.invoke([(
        "human",
        FEEDBACK_PROMPT.format(resume_md=resume_md, job_description=job_description),
    )])

    print(f"ATS Score: {audit.ats_score}")
    os.makedirs("Documents", exist_ok=True)
    with open("Documents/feedback.json", "w", encoding="utf-8") as f:
        f.write(audit.model_dump_json(indent=2))

    # ── Step 2: Rewrite resume (creative, higher temperature) ──
    rewrite_llm = llm.bind(temperature=0.6)

    IMPROVE_PROMPT = """
        You are a senior ATS optimization specialist and professional resume writer.

        Rewrite the resume below by applying EVERY improvement listed, while strictly
        following these rules:

        ### Content Rules
        - DO NOT fabricate experience, skills, certifications, or achievements.
        - DO NOT remove any real information from the original resume.
        - Rewrite bullets with strong action verbs and quantified impact where implied.
        - Naturally weave in keywords from the job description wherever they truthfully apply.
        - Fix all spelling and grammar errors identified in the improvements.

        ### Structure Rules
        - Use standard ATS-friendly section headings in this order:
          CONTACT | SUMMARY | SKILLS | EXPERIENCE | PROJECTS | EDUCATION | CERTIFICATIONS
        - Each section heading must be a Markdown ## heading.
        - CONTACT: full name, email, phone, location, and profile links each on its own line.
        - EXPERIENCE/PROJECTS: title, organization, date range, then 3–5 bullet points.

        ### Formatting Rules
        - Single-column Markdown only — no tables, images, HTML, or columns.
        - Use `-` for all bullet points.
        - Maximum 2 pages worth of content.
        - Output ONLY the improved resume in Markdown — no commentary, no fences.

        --- RESUME START ---
        {resume_md}
        --- RESUME END ---

        --- IMPROVEMENTS START ---
        {improvements}
        --- IMPROVEMENTS END ---

        --- JOB DESCRIPTION START ---
        {job_description}
        --- JOB DESCRIPTION END ---
    """

    md_response = rewrite_llm.invoke([(
        "human",
        IMPROVE_PROMPT.format(
            resume_md=resume_md,
            improvements=audit.model_dump_json(indent=2, include={"improvements"}),
            job_description=job_description,
        ),
    )])
    improved_resume = md_response.content

    # ── Step 3: Convert to LaTeX ──
    LATEX_PROMPT = r"""
        You are an expert LaTeX typesetter specializing in professional resumes.

        Convert the following improved resume into a clean, compilable LaTeX document.

        ### LaTeX Requirements
        - Use the `article` document class with 10pt or 11pt font.
        - Set margins to 0.5in on all sides using the `geometry` package.
        - Use ONLY these standard packages: geometry, enumitem, titlesec, hyperref, fontenc, inputenc, xcolor.
        - DO NOT use any custom class files, exotic packages, or fonts that require special installation.
        - The document MUST compile with `pdflatex` out of the box.

        ### Layout Rules
        - Single-column layout — no multicols, no minipages side by side.
        - Name as a centered bold header at the top.
        - Contact details separated by pipes (|) with hyperlinks where appropriate.
        - Each section uses a bold uppercase heading with a horizontal rule underneath.
        - Experience/Project entries: bold title, italic org/date, then itemize bullet points.
        - Skills: comma-separated by category — NOT bullet points.
        - Keep it to 1–2 pages.

        ### Output Rules
        - Output ONLY raw LaTeX starting with `\documentclass` and ending with `\end{{document}}`.
        - No markdown fences, no explanations, no commentary.

        --- RESUME START ---
        {improved_resume}
        --- RESUME END ---
    """

    latex_response = rewrite_llm.invoke([(
        "human",
        LATEX_PROMPT.format(improved_resume=improved_resume),
    )])

    # ── Save outputs ──
    with open("Documents/Improved_Resume.md", "w", encoding="utf-8") as f:
        f.write(improved_resume)
    with open("Documents/Improved_Resume.tex", "w", encoding="utf-8") as f:
        f.write(latex_response.content)

    state["ats_score"]      = audit.ats_score
    state["improved_resume"] = improved_resume
    state["resume_latex"]    = latex_response.content
    return state


def tex_to_pdf(state: AgentState) -> AgentState:
    import shutil
    tex_path = os.path.abspath("Documents/Improved_Resume.tex")
    out_dir  = os.path.abspath("Documents")

    pdflatex_bin = shutil.which("pdflatex")
    if not pdflatex_bin:
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\miktex-pdflatex.exe"),
            r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe",
            r"C:\Program Files\MiKTeX\miktex\bin\x64\miktex-pdflatex.exe",
            r"C:\Program Files (x86)\MiKTeX\miktex\bin\x64\pdflatex.exe",
            r"C:\Program Files (x86)\MiKTeX\miktex\bin\x64\miktex-pdflatex.exe",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                pdflatex_bin = candidate
                break

    if not pdflatex_bin:
        pdflatex_bin = "pdflatex"

    try:
        result = subprocess.run(
            [pdflatex_bin, "-interaction=nonstopmode", "-output-directory", out_dir, tex_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print("PDF generated: Documents/Improved_Resume.pdf")
        else:
            print("pdflatex warnings/errors (may still have produced a PDF):")
            log_lines = result.stdout.strip().splitlines()
            for line in log_lines[-20:]:
                print(f"  {line}")
    except FileNotFoundError:
        print("ERROR: pdflatex not found. Install MiKTeX: https://miktex.org/download")
    except subprocess.TimeoutExpired:
        print("ERROR: pdflatex timed out after 60 seconds.")

    return state


# ── Build and run the LangGraph pipeline ──
graph = StateGraph(AgentState)
graph.add_node("md", md)
graph.add_node("analyze_and_improve", analyze_and_improve)
graph.add_node("tex_to_pdf", tex_to_pdf)

graph.add_edge(START, "md")
graph.add_edge("md", "analyze_and_improve")
graph.add_edge("analyze_and_improve", "tex_to_pdf")
graph.add_edge("tex_to_pdf", END)

app = graph.compile()

# ── Collect user inputs before running the pipeline ──
file_path       = "Documents/Resume.pdf"
job_description = input("Enter the job description: ").strip()

result = app.invoke({
    "file_path":       file_path,
    "resume_md":       "",
    "job_description": job_description,
    "ats_score":       0,
    "improved_resume": "",
    "resume_latex":    "",
})

print(f"\n=== ATS SCORE: {result['ats_score']} / 100 ===")
print("\n=== IMPROVED RESUME ===")
print(result["improved_resume"])
print("\n=== FILES SAVED ===")
print("Feedback: Documents/feedback.json")
print("Markdown: Documents/Improved_Resume.md")
print("LaTeX:    Documents/Improved_Resume.tex")
