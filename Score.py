## This part Takes the PDF and converts it into JSON format
from dotenv import load_dotenv
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
import pymupdf4llm
import os
from rich.console import Console
from rich.markdown import Markdown





load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


model= ChatGoogleGenerativeAI(model="gemini-2.5-flash",temperature=0,api_key=api_key)


## This part takes the JOB description as user input and comparest it with the Resume and gives the score based on a scale of 1 to 100

def read_md_file_plain(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
job_description = read_md_file_plain("job_description.md")
md_text = read_md_file_plain("ats_corrected.md")
prompt = read_md_file_plain("prompt_sys.md")

messages=[
    {"role":"system","content":prompt + job_description},
    {"role":"user","content":md_text}
]
response_score=model.invoke(messages)

messages1=[
    {"role":"system","content":"Give a feedback based on the job descreption so that the resume can be improved to score more than 90 also make sure that the resume is ATS optimized,readable and structured,make sure to include the job title in the resume.Know about the candidate so you do not miss any important details like Education,Experience,Skills,Projects,etc."+ job_description},
    {"role":"user","content":md_text}
]
response_ats=model.invoke(messages1)

## Save the response to a markdown file
output_file_ats = "ats_feedback.md"
with open(output_file_ats, "w", encoding="utf-8") as f:
    f.write(response_ats.content)

output_file_score = "ats_score.txt"
with open(output_file_score, "w", encoding="utf-8") as f:
    f.write(response_score.content)