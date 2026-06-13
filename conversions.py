import os
import json
from docling.document_converter import DocumentConverter

class Conversion:
    def __init__(self, file_path):
        self.source = file_path  # file path or URL
        self.converter = DocumentConverter()
        self.doc = self.converter.convert(self.source).document

    def to_md(self):
        md_file = self.doc.export_to_markdown()
        os.makedirs("Documents", exist_ok=True)
        with open("Documents/Resume_output.md", "w") as f:
            f.write(md_file)
        return md_file