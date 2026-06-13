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
    md_filepath:str
    analysis:SchemaFeedback
    improved_resume: str
    resume_latex: str



def md(state: AgentState):
    file_path = state["file_path"]
    state["resume_md"] = Conversion(file_path).to_md()
    return state


def processing(state: AgentState) -> AgentState:
    llm = ChatNVIDIA(
        model=os.getenv("MODEL"),
        api_key=os.getenv("NVIDIA_API_KEY"),
        temperature=0.5,
        max_completion_tokens=4000,
        top_p=1,
    )
    
    structured_llm =llm.with_structured_output(SchemaFeedback)

    FEEDBACK_PROMPT = """
        You are a senior ATS expert and professional resume coach.

        Evaluate the resume below and return a structured JSON response with exactly two top-level keys:

        1. "ats_score" — An integer from 0 to 100 representing ATS performance. Consider:
            - Keyword relevance to common industry roles
            - Measurable achievements and impact metrics
            - Standard section headings (Experience, Education, Skills, etc.)
            - Absence of tables, columns, graphics, or non-parseable formatting
            - Appropriate action verbs
            - Spelling and grammar quality
            - Contact information completeness

        2. "improvements" — A list of improvement objects. Each must have:
            - "category": one of ["Keywords", "Formatting", "Impact", "Structure", "Skills", "Contact", "Grammar", "ATS Compatibility"]
            - "priority": one of ["High", "Medium", "Low"]
            - "issue": a short description of the specific problem found
            - "suggestion": a concrete, actionable fix the candidate should apply

        Return ONLY valid JSON. No markdown fences, no explanations outside the JSON.

        --- RESUME START ---
        {resume_md}
        --- RESUME END ---
    """

    response = structured_llm.invoke([("human", FEEDBACK_PROMPT.format(resume_md=state.get("resume_md", "")))])
    ats_score = response.ats_score
    state["analysis"] = response
    print(f"ATS Score: {ats_score}")
    with open("Documents/feedback.json", "w", encoding="utf-8") as f:
        f.write(response.model_dump_json(indent=2))
    return state


def improve(state: AgentState) -> AgentState:
    llm = ChatNVIDIA(
        model=os.getenv("MODEL"),
        api_key=os.getenv("NVIDIA_API_KEY"),
        temperature=0.6,
        max_completion_tokens=16384,
        top_p=1,
    )

    # ── Step 1: Generate improved Markdown resume ──
    IMPROVE_PROMPT = """
        You are a senior ATS optimization specialist and professional resume writer.

        You are given three inputs:
        1. The candidate's ORIGINAL resume in Markdown.
        2. A structured list of IMPROVEMENTS (from a prior ATS audit).
        3. The TARGET JOB DESCRIPTION the candidate is applying for.

        Your task is to rewrite the resume by applying EVERY improvement listed, while
        strictly following these rules:

        ### Content Rules
        - DO NOT fabricate experience, skills, certifications, or achievements the candidate does not have.
        - DO NOT remove any real information from the original resume.
        - Rewrite bullet points with strong action verbs and quantified impact where the original already implies metrics (e.g., "improved scores from 65 to 90+" stays factual but gets polished).
        - Naturally weave in keywords from the JOB DESCRIPTION wherever they truthfully apply.
        - Fix all spelling and grammar errors identified in the improvements.

        ### Structure Rules
        - Use standard ATS-friendly section headings in this order:
          CONTACT | OBJECTIVE/SUMMARY | SKILLS | EXPERIENCE | PROJECTS | EDUCATION | CERTIFICATIONS
        - Each section heading must be a Markdown ## heading.
        - Ensure the CONTACT section includes: full name, email, phone, location, and profile links (LinkedIn, GitHub, etc.) each on its own line.
        - Under EXPERIENCE and PROJECTS, each entry must have: title, organization/context, date range, and 3-5 bullet points.

        ### Formatting Rules
        - Output clean, single-column Markdown only — no tables, no images, no HTML tags, no columns.
        - Use `-` for all bullet points.
        - Keep the resume to a maximum of 2 pages worth of content.
        - Do not include any commentary, explanations, or markdown fences — output ONLY the improved resume in Markdown.

        --- ORIGINAL RESUME START ---
        {resume_md}
        --- ORIGINAL RESUME END ---

        --- IMPROVEMENTS START ---
        {feedback}
        --- IMPROVEMENTS END ---

        --- JOB DESCRIPTION START ---
        {job_description}
        --- JOB DESCRIPTION END ---
    """

    response = llm.invoke([("human", IMPROVE_PROMPT.format(resume_md=state.get("resume_md", ""), feedback=state["analysis"].model_dump_json(indent=2) if state.get("analysis") else "", job_description=state.get("job_description", "")))])
    state["improved_resume"] = response.content

    # ── Step 2: Convert the improved resume to LaTeX ──
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
        - Contact details (email, phone, location, links) on one or two lines below the name, separated by pipes (|), with hyperlinks where appropriate.
        - Each section (Summary, Skills, Experience, Projects, Education, Certifications) uses a bold uppercase heading with a horizontal rule (`\hrule` or `\rule`) underneath.
        - Experience and Project entries: bold title, italic organization/date on the same or next line, followed by an `itemize` list of bullet points.
        - Skills section: comma-separated list grouped by category (e.g., Languages, Frameworks, Tools) — NOT bullet points.
        - Keep it to 1-2 pages.

        ### Output Rules
        - Output ONLY the raw LaTeX source code starting with `\documentclass` and ending with `\end{{document}}`.
        - No markdown fences, no explanations, no commentary before or after the LaTeX code.

        --- RESUME START ---
        {improved_resume}
        --- RESUME END ---
    """

    latex_response = llm.invoke([("human", LATEX_PROMPT.format(
        improved_resume=state["improved_resume"],
    ))])
    state["resume_latex"] = latex_response.content

    # ── Save both files ──
    os.makedirs("Documents", exist_ok=True)
    with open("Documents/Improved_Resume.md", "w", encoding="utf-8") as f:
        f.write(state["improved_resume"])
    with open("Documents/Improved_Resume.tex", "w", encoding="utf-8") as f:
        f.write(state["resume_latex"])

    return state

def tex_to_pdf(state: AgentState) -> AgentState:
    import shutil
    tex_path = os.path.abspath("Documents/Improved_Resume.tex")
    out_dir = os.path.abspath("Documents")

    # Resolve pdflatex path
    pdflatex_bin = shutil.which("pdflatex")
    if not pdflatex_bin:
        # Check standard Windows MiKTeX installation locations
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
        pdflatex_bin = "pdflatex"  # Fallback to default name to trigger FileNotFoundError below

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
            # Print only the last 20 lines of log to avoid flooding the console
            log_lines = result.stdout.strip().splitlines()
            for line in log_lines[-20:]:
                print(f"  {line}")
    except FileNotFoundError:
        print("ERROR: pdflatex not found. Install a LaTeX distribution:")
        print("  Windows: https://miktex.org/download")
        print("  Then re-run the script.")
    except subprocess.TimeoutExpired:
        print("ERROR: pdflatex timed out after 60 seconds.")

    return state


# ── Build and run the LangGraph pipeline ──
graph = StateGraph(AgentState)
graph.add_node("md", md)
graph.add_node("processing", processing)
graph.add_node("improve", improve)
graph.add_node("tex_to_pdf", tex_to_pdf)

graph.add_edge(START, "md")
graph.add_edge("md", "processing")
graph.add_edge("processing", "improve")
graph.add_edge("improve", "tex_to_pdf")
graph.add_edge("tex_to_pdf", END)

app = graph.compile()

# ── Collect user inputs before running the pipeline ──
file_path = "Documents/Resume.pdf"
job_description = input("Enter the job description: ").strip()

result = app.invoke({
    "file_path": file_path,
    "resume_md": "",
    "job_description": job_description,
    "md_filepath": "",
    "analysis": None,
    "improved_resume": "",
    "resume_latex": "",
})

print("=== ATS FEEDBACK ===")
print(result["analysis"].model_dump_json(indent=2))
print("\n=== IMPROVED RESUME ===")
print(result["improved_resume"])
print("\n=== FILES SAVED ===")
print("Markdown: Documents/Improved_Resume.md")
print("LaTeX:    Documents/Improved_Resume.tex")
