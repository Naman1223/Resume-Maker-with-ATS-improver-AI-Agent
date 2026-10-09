from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def read_md_file_plain(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

feedback    = read_md_file_plain("ats_feedback.md")
resume_text = read_md_file_plain("ats_corrected.md")

def ats_corrected() -> str:
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.3, api_key=api_key)
    messages = [
        # Single system message — merges the old two system messages
        {"role": "system", "content": (
            "You are an expert Executive Resume Writer and ATS (Applicant Tracking System) "
            "Optimization Specialist. Your goal is to rewrite a candidate's resume to score "
            "higher than 90 on an ATS system based on the ATS feedback provided below.\n\n"
            "Rules:\n"
            "- Do NOT invent employers, dates, metrics, or tools not already present in the resume.\n"
            "- You may add commonly expected soft skills only if they are genuinely consistent "
            "with the candidate's background and role — never fabricate specifics.\n"
            "- Return ONLY the rewritten resume with no commentary.\n\n"
            "ATS Feedback:\n" + feedback
        )},
        # Single user message — merges the old instruction + resume into one turn
        {"role": "user", "content": (
            "Rewrite the resume below based on the ATS feedback above. "
            "Do not include anything other than the rewritten resume.\n\n"
            "Resume:\n" + resume_text
        )}
    ]
    response = model.invoke(messages)
    return response.content

response_ats = ats_corrected()

with open("ats_corrected.md", "w", encoding="utf-8") as f:
    f.write(response_ats)
