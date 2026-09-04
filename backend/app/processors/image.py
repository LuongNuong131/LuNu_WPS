from typing import List

from PIL import Image

from app.processors.base import DocumentProcessor


class ImageConvertProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        image = Image.open(input_paths[0]).convert("RGB")
        try:
            image.save(output_path, "PNG", optimize=True)
            return True
        finally:
            image.close()


class ImagesToPDFProcessor(DocumentProcessor):
    def process(self, input_paths: List[str], output_path: str, options: dict = None) -> bool:
        if not input_paths:
            raise ValueError("Không có ảnh đầu vào.")
        images = []
        try:
            for path in input_paths:
                image = Image.open(path).convert("RGB")
                images.append(image)
            images[0].save(output_path, "PDF", resolution=150.0, save_all=True, append_images=images[1:])
            return True
        finally:
            for image in images:
                image.close()
