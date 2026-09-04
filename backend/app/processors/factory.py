from app.processors.pdf_to_excel import PDFToExcelProcessor
from app.processors.pdf_manager import MergePDFProcessor, SplitPDFProcessor

def get_processor(tool_slug: str):
    if tool_slug == "pdf-to-excel":
        return PDFToExcelProcessor()
    elif tool_slug == "merge-pdf":
        return MergePDFProcessor()
    elif tool_slug == "split-pdf":
        return SplitPDFProcessor()
    
    return None