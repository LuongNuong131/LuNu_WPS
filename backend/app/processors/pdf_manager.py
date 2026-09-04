import os
import zipfile
from typing import List

import fitz

from app.processors.base import DocumentProcessor


class MergePDFProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        if len(input_paths) < 2:
            raise ValueError("Cần ít nhất 2 file để thực hiện ghép PDF.")
        merged = fitz.open()
        try:
            for path in input_paths:
                with fitz.open(path) as pdf:
                    merged.insert_pdf(pdf)
            merged.save(output_path, garbage=4, deflate=True)
            return True
        finally:
            merged.close()


class SplitPDFProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        if not input_paths:
            raise ValueError("Không có file đầu vào.")
        with fitz.open(input_paths[0]) as pdf:
            if pdf.page_count <= 1:
                raise ValueError("File PDF cần có ít nhất 2 trang để tách.")
            base_name = os.path.splitext(os.path.basename(input_paths[0]))[0]
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for index in range(pdf.page_count):
                    part = fitz.open()
                    try:
                        part.insert_pdf(pdf, from_page=index, to_page=index)
                        filename = f"{base_name}_page_{index + 1}.pdf"
                        temp_path = os.path.join(os.path.dirname(output_path), filename)
                        part.save(temp_path)
                        archive.write(temp_path, filename)
                        os.remove(temp_path)
                    finally:
                        part.close()
        return True


class CompressPDFProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        with fitz.open(input_paths[0]) as source:
            source.save(output_path, garbage=4, clean=True, deflate=True)
        return True


class RotatePDFProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        degrees = int((options or {}).get("degrees", 90))
        if degrees not in (90, 180, 270):
            raise ValueError("Góc xoay phải là 90, 180 hoặc 270 độ.")
        with fitz.open(input_paths[0]) as pdf:
            for page in pdf:
                page.set_rotation((page.rotation + degrees) % 360)
            pdf.save(output_path, garbage=4, deflate=True)
        return True


class ExtractPagesProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        pages = (options or {}).get("pages")
        with fitz.open(input_paths[0]) as source:
            if not pages:
                raise ValueError("Vui lòng chọn danh sách trang cần trích xuất, ví dụ: 1,3-5.")
            indexes = _parse_page_ranges(pages, source.page_count)
            output = fitz.open()
            try:
                for index in indexes:
                    output.insert_pdf(source, from_page=index, to_page=index)
                output.save(output_path, garbage=4, deflate=True)
            finally:
                output.close()
        return True


class DeletePagesProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        pages = (options or {}).get("pages")
        with fitz.open(input_paths[0]) as source:
            if not pages:
                raise ValueError("Vui lòng chọn danh sách trang cần xóa, ví dụ: 2,4.")
            delete_indexes = set(_parse_page_ranges(pages, source.page_count))
            if len(delete_indexes) >= source.page_count:
                raise ValueError("Không thể xóa toàn bộ trang trong PDF.")
            output = fitz.open()
            try:
                for index in range(source.page_count):
                    if index not in delete_indexes:
                        output.insert_pdf(source, from_page=index, to_page=index)
                output.save(output_path, garbage=4, deflate=True)
            finally:
                output.close()
        return True


class PDFToJPGProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        with fitz.open(input_paths[0]) as pdf, zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            temp_dir = os.path.dirname(output_path)
            for index, page in enumerate(pdf):
                image_path = os.path.join(temp_dir, f"page_{index + 1}.jpg")
                page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False).save(image_path)
                archive.write(image_path, os.path.basename(image_path))
                os.remove(image_path)
        return True


def _parse_page_ranges(value: str, page_count: int) -> list[int]:
    indexes: set[int] = set()
    for token in value.replace(" ", "").split(","):
        if "-" in token:
            start, end = token.split("-", 1)
            start_num, end_num = int(start), int(end)
            if start_num > end_num:
                raise ValueError("Khoảng trang không hợp lệ.")
            indexes.update(range(start_num - 1, end_num))
        else:
            indexes.add(int(token) - 1)
    if any(index < 0 or index >= page_count for index in indexes):
        raise ValueError(f"Trang phải nằm trong khoảng 1 đến {page_count}.")
    return sorted(indexes)
