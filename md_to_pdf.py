from markdown_pdf import MarkdownPdf, Section

pdf = MarkdownPdf(toc_level=1)
# Load your markdown file content
with open("ats_corrected.md", "r", encoding="utf-8") as f:
    md_content = f.read()

pdf.add_section(Section(md_content))
pdf.save("ats_corrected_resume.pdf")
