import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.graph import StateGraph, START, END
from conversions import Conversion

load_dotenv()


class AgentState(TypedDict):
    file_path: str
    resume_md: str
    job_description: str
    ats_score: int
    feedback: str
    improved_resume: str



def md(state: AgentState):
    state["file_path"] = "Documents/Resume.pdf"
    state["job_description"] = input("Enter the job description: ")
    if state["file_path"].endswith(".pdf"):
        state["resume_md"] = Conversion(state["file_path"]).pdf_to_md()
    elif state["file_path"].endswith(".docx"):
        state["resume_md"] = Conversion(state["file_path"]).docx_to_md()
    elif state["file_path"].endswith(".jpg") or state["file_path"].endswith(".png"):
        state["resume_md"] = Conversion(state["file_path"]).img_to_md()
    else:
        state["resume_md"] = Conversion(state["file_path"]).text_to_md()
    return state


def processing(prompt: str, state: AgentState) -> AgentState:
    llm = ChatNVIDIA(
        model=os.getenv("MODEL"),
        api_key=os.getenv("NVIDIA_API_KEY"),
        temperature=0.5,
        max_completion_tokens=16384,
        top_p=1,
    )

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

    response = llm.invoke([("human", FEEDBACK_PROMPT.format(resume_md=state.get("resume_md", "")))])
    state["feedback"] = response.content
    return state


result = processing("", {"resume_md": "", "job_description": "", "ats_score": 0, "feedback": "", "improved_resume": ""})
print(result["feedback"])
