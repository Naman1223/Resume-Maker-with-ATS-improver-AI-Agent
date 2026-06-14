# Security Policy

## Supported Versions

Only the latest commit on `main` receives security fixes.
Older tags are unsupported.

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| Any pinned tag | ❌ |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately via one of these channels:

- **GitHub private advisory** — [Security → Advisories → Report a vulnerability](../../security/advisories/new) *(preferred)*
- **Email** — contact the maintainer directly through the email listed on their GitHub profile

Please include:
- A clear description of the vulnerability
- Steps to reproduce it
- The potential impact
- Any suggested fix, if you have one

You should receive an acknowledgement within **72 hours**. If you do not, follow up by email. There is no formal bug bounty programme for this project.

---

## Security Considerations

This project is a **local CLI tool**. It is not designed to be exposed as a web service or API. The threat model below assumes single-user local execution.

### API Keys

- The NVIDIA API key is loaded from a `.env` file via `python-dotenv`.
- **Never commit `.env` to version control.** The `.gitignore` must include `.env`.
- The API key is passed in memory to `langchain-nvidia-ai-endpoints` and never written to disk by this project.
- Rotate your key immediately if you suspect it has been exposed.

### Resume Content and Data Privacy

- Resume text (extracted from the uploaded PDF) is sent to NVIDIA's hosted LLM API for rewriting.
- Do not process resumes containing sensitive identifiers (SSNs, passport numbers, bank details) unless you have reviewed NVIDIA's data retention and privacy policies.
- The original resume PDF, extracted Markdown, ATS feedback JSON, and improved outputs are all written to the `Documents/` directory in plaintext. Secure or delete this directory after use if working on a shared machine.

### LaTeX Compilation (Subprocess Risk)

- `tex_to_pdf` calls `pdflatex` via `subprocess.run` with the LLM-generated `.tex` file as input.
- LaTeX supports shell-escape commands (`\write18`) that can execute arbitrary shell commands. This project does **not** pass `--shell-escape` to `pdflatex`, which means shell commands embedded in generated LaTeX are blocked by default.
- Do not add `--shell-escape` to the `subprocess.run` call; doing so would allow an adversarially crafted LLM response to execute arbitrary code on your machine.
- Verify that your MiKTeX or TeX Live installation has `shell_escape = f` (forbidden) set in its `texmf.cnf`.

### File Path Handling

- The `file_path` field in `AgentState` is passed directly to the `Conversion` class. It is not sanitised against path traversal.
- This is acceptable for a local single-user tool, but do not expose `file_path` to user-controlled input over a network without validation.

### Dependency Supply Chain

- This project depends on `langchain-nvidia-ai-endpoints`, `langgraph`, `pydantic`, and optionally `pyspellchecker`.
- Pin dependencies with exact versions in `requirements.txt` and audit them with `pip audit` before use in any sensitive environment.
- Run `pip audit` periodically to catch known CVEs in pinned packages:
  ```
  pip install pip-audit
  pip-audit
  ```

### No Network Exposure

- This tool is not a server and opens no ports. If you wrap it in a web framework (FastAPI, Flask, etc.) in the future, re-evaluate this security model entirely — especially the subprocess and file path concerns.

---

## Out of Scope

The following are accepted limitations of a local CLI tool and are not treated as security issues:

- Absence of authentication or authorisation (single-user local tool by design)
- Resume content being visible in plaintext in `Documents/`
- No encryption of `.env` at rest (standard practice for local development)

---

## Recommended Local Setup

```bash
# 1. Keep .env out of git
echo ".env" >> .gitignore
echo "Documents/" >> .gitignore

# 2. Audit dependencies
pip install pip-audit
pip-audit

# 3. Confirm pdflatex shell-escape is off
kpsewhich texmf.cnf          # find the config file
grep shell_escape "$(kpsewhich texmf.cnf)"  # should show: shell_escape = f
```
