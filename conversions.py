from langchain_pymupdf4llm import PyMuPDF4LLMLoader
# Convert PDF to markdown text
def extract_text(pdf_path):
    loader = PyMuPDF4LLMLoader(pdf_path)
    docs = loader.load()
    md_text = "".join([doc.page_content for doc in docs])
    return md_text


