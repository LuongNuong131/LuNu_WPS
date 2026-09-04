from abc import ABC, abstractmethod
from typing import List

class DocumentProcessor(ABC):
    @abstractmethod
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        """
        Hàm xử lý chính.
        input_paths: Danh sách đường dẫn các file đầu vào (1 hoặc nhiều file).
        output_path: Đường dẫn file đầu ra.
        Trả về True nếu thành công, ném Exception nếu có lỗi.
        """
        pass