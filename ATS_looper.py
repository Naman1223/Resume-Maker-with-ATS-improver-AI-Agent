from dotenv import load_dotenv
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
import re
import os
from rich.console import Console
from rich.markdown import Markdown
import subprocess
import time
from conversions import extract_text
load_dotenv()

console = Console()

pdf_path = r"Resume.pdf"
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

TARGET_SCORE = 90
MAX_ITERATIONS = 5
counter = 0

def read_ats_score():
    """Read and extract the numeric ATS score from ats_score.txt."""
    try:
        with open("ats_score.txt", "r", encoding="utf-8") as f:
            content = f.read()
        # Extract the first integer (0-100) from the score file
        match = re.search(r'\b(\d{1,3})\b', content)
        if match:
            return int(match.group(1))
    except FileNotFoundError:
        pass
    return None

while counter < MAX_ITERATIONS:
    console.print(f"\n[bold cyan]--- Iteration {counter + 1}/{MAX_ITERATIONS} ---[/bold cyan]")

    # Score the current resume
    console.print("[yellow]Scoring resume...[/yellow]")
    Score = subprocess.run([sys.executable, "Score.py"], capture_output=True, text=True)

    # Check score — exit early if target is reached
    current_score = read_ats_score()
    if current_score is not None:
        console.print(f"[bold]ATS Score: {current_score}/100[/bold]")
        if current_score >= TARGET_SCORE:
            console.print(f"[bold green]✓ Target score of {TARGET_SCORE} reached! Stopping early and saving Gemini calls.[/bold green]")
            break
    else:
        console.print("[red]Could not read score — continuing anyway.[/red]")

    # Apply corrections only if score not yet met
    console.print("[yellow]Applying ATS corrections...[/yellow]")
    result = subprocess.run([sys.executable, "Correction.py"], capture_output=True, text=True)
    counter += 1

console.print(f"\n[bold]Optimization complete after {counter} iteration(s).[/bold]")

md_to_pdf_output = subprocess.run([sys.executable, "md_to_pdf.py"], capture_output=True, text=True)
md_to_pdf_output = md_to_pdf_output.stdout
