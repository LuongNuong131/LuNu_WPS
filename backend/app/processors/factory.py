from app.processors.pdf_to_excel import PDFToExcelProcessor
from app.processors.pdf_manager import (
    CompressPDFProcessor,
    DeletePagesProcessor,
    ExtractPagesProcessor,
    MergePDFProcessor,
    PDFToJPGProcessor,
    RotatePDFProcessor,
    SplitPDFProcessor,
)
from app.processors.office import OfficeToPDFProcessor, PDFToWordProcessor
from app.processors.image import ImageConvertProcessor, ImagesToPDFProcessor


PROCESSORS = {
    "pdf-to-excel": PDFToExcelProcessor,
    "merge-pdf": MergePDFProcessor,
    "split-pdf": SplitPDFProcessor,
    "compress-pdf": CompressPDFProcessor,
    "rotate-pdf": RotatePDFProcessor,
    "pdf-to-jpg": PDFToJPGProcessor,
    "extract-pages": ExtractPagesProcessor,
    "delete-pages": DeletePagesProcessor,
    "pdf-to-word": PDFToWordProcessor,
    "word-to-pdf": OfficeToPDFProcessor,
    "excel-to-pdf": OfficeToPDFProcessor,
    "powerpoint-to-pdf": OfficeToPDFProcessor,
    "jpg-to-pdf": ImagesToPDFProcessor,
    "image-convert": ImageConvertProcessor,
}


def get_processor(tool_slug: str):
    processor = PROCESSORS.get(tool_slug)
    return processor(tool_slug) if processor is OfficeToPDFProcessor else processor() if processor else None
