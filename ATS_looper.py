from dotenv import load_dotenv
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
import re
import os
from rich.console import Console
from rich.markdown import Markdown
import subprocess
import sys
import pymupdf4llm
import time
load_dotenv()

def extract_text(pdf_path):
    md_text = pymupdf4llm.to_markdown(pdf_path) 
    return md_text

pdf_path = r"Resume-Nitin.pdf"
md_text = extract_text(pdf_path)

with open("ats_corrected.md", "w", encoding="utf-8") as f:
    f.write(md_text)

def job_description():
    print("Enter Job Description (Ctrl+Z to save):")
    job_description = sys.stdin.read()
    return job_description
job_description = job_description()

output_file_job = "job_description.md"
with open(output_file_job, "w", encoding="utf-8") as f:
    f.write(job_description)
counter = 0

while counter < 5:
    Score = subprocess.run([sys.executable, "Score.py"], capture_output=True, text=True)
    Score_output = Score.stdout
    result = subprocess.run([sys.executable, "Correction.py"], capture_output=True, text=True)
    output = result.stdout
    counter += 1

md_to_pdf_output = subprocess.run([sys.executable, "md_to_pdf.py"], capture_output=True, text=True)
md_to_pdf_output = md_to_pdf_output.stdout
