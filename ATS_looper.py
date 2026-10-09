from dotenv import load_dotenv
import sys
import re
import os
import shutil
import subprocess
from rich.console import Console
from conversions import extract_text

load_dotenv()
console = Console()

# ── Config ───────────────────────────────────────────────────────────────────
PDF_PATH       = r"Resume.pdf"
TARGET_SCORE   = 90
MAX_ITERATIONS = 5

# ── Extract resume text ──────────────────────────────────────────────────────
md_text = extract_text(PDF_PATH)

# Save original as v0 so it can never be lost
os.makedirs("versions", exist_ok=True)
with open("versions/resume_v0.md", "w", encoding="utf-8") as f:
    f.write(md_text)
with open("ats_corrected.md", "w", encoding="utf-8") as f:
    f.write(md_text)
console.print("[bold green]✓ Original resume saved as versions/resume_v0.md[/bold green]")

# ── Job description ──────────────────────────────────────────────────────────
def get_job_description() -> str:
    """Read JD from jd.txt if present, otherwise fall back to stdin."""
    if os.path.exists("jd.txt"):
        with open("jd.txt", "r", encoding="utf-8") as f:
            jd = f.read().strip()
        console.print("[bold green]✓ Job description loaded from jd.txt[/bold green]")
        return jd
    console.print("[yellow]Enter Job Description (Ctrl+Z then Enter on Windows to finish):[/yellow]")
    return sys.stdin.read()

job_description = get_job_description()
with open("job_description.md", "w", encoding="utf-8") as f:
    f.write(job_description)

# ── Delete stale files from any previous run ─────────────────────────────────
# A leftover ats_score.txt could report a false ≥90 if Score.py fails
for stale in ("ats_score.txt", "ats_feedback.md"):
    if os.path.exists(stale):
        os.remove(stale)

# ── Helpers ──────────────────────────────────────────────────────────────────
def run_step(script: str, label: str) -> bool:
    """Run a subprocess step. Prints stderr on failure; returns success bool."""
    console.print(f"[yellow]{label}...[/yellow]")
    result = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[bold red]✗ {script} failed (exit {result.returncode}):[/bold red]")
        if result.stderr.strip():
            console.print(result.stderr)
        if result.stdout.strip():
            console.print(result.stdout)
        return False
    return True


def read_ats_score() -> "int | None":
    """Return the first 0–100 integer from ats_score.txt, or None."""
    try:
        with open("ats_score.txt", "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r'(?<!\d)(\d{1,3})(?!\d)', content)
        if match:
            val = int(match.group(1))
            if 0 <= val <= 100:
                return val
    except FileNotFoundError:
        pass
    return None


def save_version(iteration: int):
    """Snapshot the current ats_corrected.md to versions/resume_vN.md."""
    dest = f"versions/resume_v{iteration}.md"
    shutil.copy("ats_corrected.md", dest)
    console.print(f"[dim]  Saved snapshot → {dest}[/dim]")


# ── Main loop ────────────────────────────────────────────────────────────────
score_history: list = []   # [(iteration, score), ...]
counter = 0
target_reached = False

while counter < MAX_ITERATIONS:
    console.print(f"\n[bold cyan]━━━  Iteration {counter + 1}/{MAX_ITERATIONS}  ━━━[/bold cyan]")

    # 1. Score current resume
    if not run_step("Score.py", "Scoring resume"):
        console.print("[bold red]Aborting: scoring failed.[/bold red]")
        break

    current_score = read_ats_score()
    if current_score is None:
        console.print("[bold red]Could not parse a valid score — aborting.[/bold red]")
        break

    console.print(f"[bold]  ATS Score: {current_score}/100[/bold]")
    score_history.append((counter + 1, current_score))

    if current_score >= TARGET_SCORE:
        console.print(
            f"[bold green]✓ Target score of {TARGET_SCORE} reached after {counter + 1} "
            f"pass(es). No further Gemini calls needed.[/bold green]"
        )
        target_reached = True
        break

    # 2. Rewrite resume
    if not run_step("Correction.py", "Applying ATS corrections"):
        console.print("[bold red]Aborting: correction failed.[/bold red]")
        break

    counter += 1
    save_version(counter)   # snapshot after each rewrite

# ── Score the final rewrite if we exhausted all iterations ───────────────────
if not target_reached and counter == MAX_ITERATIONS:
    console.print(f"\n[yellow]Max iterations reached — scoring the final rewrite...[/yellow]")
    if run_step("Score.py", "Final scoring pass"):
        final_score = read_ats_score()
        if final_score is not None:
            score_history.append((counter + 1, final_score))
            console.print(f"[bold]  Final ATS Score: {final_score}/100[/bold]")

# ── Score history ─────────────────────────────────────────────────────────────
console.print("\n[bold]Score history:[/bold]")
for iteration, score in score_history:
    bar = "█" * (score // 5)
    console.print(f"  Iter {iteration:>2}: {score:>3}/100  {bar}")

console.print(f"\n[bold]Optimization complete after {counter} rewrite iteration(s).[/bold]")

# ── Convert to PDF ────────────────────────────────────────────────────────────
pdf_result = subprocess.run([sys.executable, "md_to_pdf.py"], capture_output=True, text=True)
if pdf_result.returncode != 0:
    console.print("[bold red]✗ PDF conversion failed:[/bold red]")
    console.print(pdf_result.stderr)
else:
    console.print("[bold green]✓ PDF generated successfully.[/bold green]")
