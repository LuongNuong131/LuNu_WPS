from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    slug: str
    name: str
    category: str
    input_extensions: tuple[str, ...]
    output_extension: str
    multiple_files: bool = False
    enabled: bool = True


TOOLS: dict[str, ToolDefinition] = {
    "pdf-to-excel": ToolDefinition("pdf-to-excel", "PDF to Excel", "PDF", (".pdf",), ".xlsx"),
    "merge-pdf": ToolDefinition("merge-pdf", "Merge PDF", "PDF", (".pdf",), ".pdf", True),
    "split-pdf": ToolDefinition("split-pdf", "Split PDF", "PDF", (".pdf",), ".zip"),
    "compress-pdf": ToolDefinition("compress-pdf", "Compress PDF", "PDF", (".pdf",), ".pdf"),
    "rotate-pdf": ToolDefinition("rotate-pdf", "Rotate PDF", "PDF", (".pdf",), ".pdf"),
    "pdf-to-jpg": ToolDefinition("pdf-to-jpg", "PDF to JPG", "PDF", (".pdf",), ".zip"),
    "extract-pages": ToolDefinition("extract-pages", "Extract pages", "PDF", (".pdf",), ".pdf"),
    "delete-pages": ToolDefinition("delete-pages", "Delete pages", "PDF", (".pdf",), ".pdf"),
    "pdf-to-word": ToolDefinition("pdf-to-word", "PDF to Word", "Office", (".pdf",), ".docx"),
    "word-to-pdf": ToolDefinition("word-to-pdf", "Word to PDF", "Office", (".doc", ".docx"), ".pdf"),
    "excel-to-pdf": ToolDefinition("excel-to-pdf", "Excel to PDF", "Office", (".xls", ".xlsx", ".csv"), ".pdf"),
    "powerpoint-to-pdf": ToolDefinition("powerpoint-to-pdf", "PowerPoint to PDF", "Office", (".ppt", ".pptx"), ".pdf"),
    "jpg-to-pdf": ToolDefinition("jpg-to-pdf", "JPG to PDF", "Images", (".jpg", ".jpeg", ".png", ".webp"), ".pdf", True),
    "image-convert": ToolDefinition("image-convert", "Convert image", "Images", (".jpg", ".jpeg", ".png", ".webp"), ".png"),
}


def get_tool(slug: str) -> ToolDefinition | None:
    return TOOLS.get(slug)


def public_tools() -> list[dict]:
    return [
        {
            "slug": tool.slug,
            "name": tool.name,
            "category": tool.category,
            "input_extensions": list(tool.input_extensions),
            "output_extension": tool.output_extension,
            "multiple_files": tool.multiple_files,
            "enabled": tool.enabled,
        }
        for tool in TOOLS.values()
    ]
