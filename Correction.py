from dotenv import load_dotenv
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
import pymupdf4llm
import os
from rich.console import Console
from rich.markdown import Markdown
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def read_md_file_plain(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

content = read_md_file_plain("ats_feedback.md")
ats_corrected1 = read_md_file_plain("ats_corrected.md")
console = Console()
feedback_ats = Markdown(content)
ats_ = Markdown(ats_corrected1)

def ats_corrected():
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite",temperature=1,api_key=api_key)
    messages=[
    {"role":"system","content":"""You are an expert Executive Resume Writer and ATS (Applicant Tracking System) Optimization Specialist. 
        Your goal is to rewrite a candidate's resume to score higher than 90 on an ATS system based on the ATS feedback.You can use your creativity to write soft skills which are not mentioned in the ATS feedback and is common and required for the job make sure not add any irrelevant soft skills.
        """},
    {"role":"system","content":content},
    {"role":"user","content":"Fix this following resume based on the ATS feedback.Do not include any thing other than the fixed resume"},
    {"role":"user","content":ats_corrected1}
    ]
    response_ats=model.invoke(messages)
    return response_ats.content

response_ats = ats_corrected()


output_file = "ats_corrected.md"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(response_ats)
