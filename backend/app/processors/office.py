import os
import shutil
import subprocess
from typing import List

import fitz
from docx import Document

from app.processors.base import DocumentProcessor


class OfficeToPDFProcessor(DocumentProcessor):
    def __init__(self, tool_slug: str):
        self.tool_slug = tool_slug

    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        source = input_paths[0]
        output_dir = os.path.dirname(output_path)
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, source],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        generated = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(source))[0]}.pdf")
        if result.returncode != 0 or not os.path.exists(generated):
            raise RuntimeError(result.stderr.strip() or "LibreOffice không thể chuyển đổi file.")
        if os.path.abspath(generated) != os.path.abspath(output_path):
            shutil.move(generated, output_path)
        return True


class PDFToWordProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        document = Document()
        with fitz.open(input_paths[0]) as pdf:
            for index, page in enumerate(pdf):
                if index:
                    document.add_page_break()
                text = page.get_text("text").strip()
                document.add_paragraph(text or "[Trang này không có lớp văn bản. OCR sẽ được hỗ trợ ở module tiếp theo.]")
        document.save(output_path)
        return True
