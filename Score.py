from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, api_key=api_key)

def read_md_file_plain(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

job_description = read_md_file_plain("job_description.md")
md_text         = read_md_file_plain("ats_corrected.md")
prompt          = read_md_file_plain("Documents/prompt_sys.md")  # fixed path

## Score the resume against the job description
messages = [
    {"role": "system", "content": prompt + job_description},
    {"role": "user",   "content": md_text}
]
response_score = model.invoke(messages)

## Generate ATS feedback
messages1 = [
    {"role": "system", "content": (
        "Give feedback based on the job description so that the resume can be improved "
        "to score more than 90. Ensure the resume is ATS optimized, readable, and structured. "
        "Include the job title in the resume. Cover all candidate details: "
        "Education, Experience, Skills, Projects, etc.\n\n" + job_description
    )},
    {"role": "user", "content": md_text}
]
response_ats = model.invoke(messages1)

## Save responses
with open("ats_feedback.md", "w", encoding="utf-8") as f:
    f.write(response_ats.content)

with open("ats_score.txt", "w", encoding="utf-8") as f:
    f.write(response_score.content)
