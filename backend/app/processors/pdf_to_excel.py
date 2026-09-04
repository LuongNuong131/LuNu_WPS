import pdfplumber
import pandas as pd
from app.processors.base import DocumentProcessor

class PDFToExcelProcessor(DocumentProcessor):
    def process(self, input_path: str, output_path: str, options: dict = None) -> bool:
        df_list = []
        
        try:
            with pdfplumber.open(input_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables):
                        # Lọc các bảng rỗng hoặc không đủ dòng/cột
                        if table and len(table) > 1:
                            # Dòng đầu tiên làm Header
                            headers = table[0]
                            # Xử lý trường hợp header bị None
                            headers = [str(h) if h is not None else f"Column_{i}" for i, h in enumerate(headers)]
                            
                            df = pd.DataFrame(table[1:], columns=headers)
                            df_list.append(df)
                            
            if not df_list:
                raise ValueError("Không tìm thấy dữ liệu bảng (table) nào trong file PDF này.")
                
            # Ghi ra file Excel nhiều sheet
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for i, df in enumerate(df_list):
                    df.to_excel(writer, sheet_name=f"Table_{i+1}", index=False)
                    
            return True
            
        except Exception as e:
            raise Exception(f"Lỗi khi xử lý PDF: {str(e)}")