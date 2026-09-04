import fitz
import zipfile
import os
from typing import List
from app.processors.base import DocumentProcessor

class MergePDFProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        if len(input_paths) < 2:
            raise ValueError("Cần ít nhất 2 file để thực hiện ghép (Merge).")
        
        try:
            merged_pdf = fitz.open()
            for path in input_paths:
                with fitz.open(path) as pdf:
                    merged_pdf.insert_pdf(pdf)
                    
            merged_pdf.save(output_path)
            merged_pdf.close()
            return True
        except Exception as e:
            raise Exception(f"Lỗi khi ghép PDF: {str(e)}")

class SplitPDFProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        if not input_paths:
            raise ValueError("Không có file đầu vào.")
            
        input_path = input_paths[0]
        output_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        
        try:
            with fitz.open(input_path) as pdf:
                if pdf.page_count <= 1:
                    raise ValueError("File PDF chỉ có 1 trang, không thể cắt.")
                    
                # Nén các trang PDF rời rạc vào một file ZIP
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for i in range(pdf.page_count):
                        new_pdf = fitz.open()
                        new_pdf.insert_pdf(pdf, from_page=i, to_page=i)
                        
                        page_filename = f"{base_name}_page_{i+1}.pdf"
                        page_path = os.path.join(output_dir, page_filename)
                        new_pdf.save(page_path)
                        new_pdf.close()
                        
                        zipf.write(page_path, page_filename)
                        os.remove(page_path) # Dọn file tạm
                        
            return True
        except Exception as e:
            raise Exception(f"Lỗi khi cắt PDF: {str(e)}")