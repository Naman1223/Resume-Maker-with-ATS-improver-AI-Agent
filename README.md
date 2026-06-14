# Resume Maker with ATS Improver AI Agent

An intelligent agentic workflow that analyzes your resume against a job description, scores it against ATS criteria, rewrites it for maximum compatibility, and produces a polished **LaTeX-compiled PDF** — all in a single run.

Built with **LangGraph**, **NVIDIA NIM**, **Docling**, and **pdflatex**.

---

## Features

- **PDF → Markdown extraction** via Docling (handles text-based and scanned PDFs)
- **ATS Scoring** — deterministic, rubric-based score (0–100) against the provided job description:
  - Keywords match: 30 pts
  - Measurable achievements: 20 pts
  - Standard section headings: 15 pts
  - ATS-safe formatting: 15 pts
  - Action verbs: 10 pts
  - Contact completeness: 5 pts
  - Grammar/spelling: 5 pts
- **Structured feedback** — categorized improvements with priority levels (High / Medium / Low)
- **Intelligent rewrite** — applies every improvement while staying factually accurate to the original resume
- **LaTeX PDF generation** — compiles a clean, single-column ATS-friendly PDF via `pdflatex`

---

## Pipeline

```
PDF ──► md ──► analyze_and_improve ──► tex_to_pdf ──► PDF output
               │
               ├─ Step 1: Score & audit (temperature=0, structured output)
               ├─ Step 2: Rewrite resume in Markdown  (temperature=0.6)
               └─ Step 3: Convert Markdown → LaTeX    (temperature=0.6)
```

---

## Prerequisites

- Python 3.10+
- An **NVIDIA NIM API key** — get one free at [build.nvidia.com](https://build.nvidia.com)
- A LaTeX distribution for PDF compilation:
  - **Windows**: [MiKTeX](https://miktex.org/download)
  - **Mac**: MacTeX (`brew install --cask mactex`)
  - **Linux**: `sudo apt install texlive-full`

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Naman1223/Resume-Maker-with-ATS-improver-AI-Agent.git
   cd Resume-Maker-with-ATS-improver-AI-Agent
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Mac/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```env
   NVIDIA_API_KEY=your_nvidia_nim_api_key_here
   MODEL=meta/llama-3.1-70b-instruct
   ```
   You can use any model available on NVIDIA NIM (e.g. `mistralai/mistral-7b-instruct-v0.3`).

---

## Usage

1. **Place your resume PDF** at:
   ```
   Documents/Resume.pdf
   ```

2. **Run the agent:**
   ```bash
   python main.py
   ```

3. **Paste your job description** when prompted and press Enter.

4. **Wait for the pipeline to finish** — it will print the ATS score and save all outputs.

---

## Output Files

All outputs are saved in the `Documents/` folder:

| File | Description |
|------|-------------|
| `Resume_output.md` | Raw Markdown extracted from your original PDF |
| `feedback.json` | ATS score + structured list of improvements |
| `Improved_Resume.md` | Rewritten resume in Markdown |
| `Improved_Resume.tex` | LaTeX source of the improved resume |
| `Improved_Resume.pdf` | Final compiled PDF (requires pdflatex) |

---

## File Structure

```
├── main.py            # LangGraph pipeline (md → analyze_and_improve → tex_to_pdf)
├── conversions.py     # PDF → Markdown conversion using Docling
├── requirements.txt   # Python dependencies
├── .env               # API keys (not committed)
└── Documents/
    ├── Resume.pdf              # Your input resume (place here)
    ├── Resume_output.md        # Extracted Markdown
    ├── feedback.json           # ATS audit results
    ├── Improved_Resume.md      # Rewritten resume
    ├── Improved_Resume.tex     # LaTeX source
    └── Improved_Resume.pdf     # Final PDF output
```

---

## Notes

- The scoring uses `temperature=0` for deterministic, consistent results across runs.
- Only the `improvements` list (not the full audit) is passed to the rewrite step, reducing token usage.
- If `pdflatex` is not found, the `.tex` file is still saved — you can compile it manually.

---

## Contributing

Contributions are welcome! Feel free to open an issue or submit a Pull Request.
