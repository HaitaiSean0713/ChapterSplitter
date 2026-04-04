"""
Merger — 統一出口，根據檔案類型呼叫對應 splitter。
"""
from splitter.pdf_splitter import extract_pages as pdf_extract
from splitter.docx_splitter import extract_chapters_docx
from splitter.txt_splitter import extract_chapters_txt


def merge_selected(
    file_path: str,
    file_type: str,
    chapters: list[dict],
    selected_titles: list[str],
    page_shift: int = 0
) -> tuple[bytes, str]:
    """
    回傳 (bytes, mime_type)。
    輸出格式與原始檔一致。
    """
    if not selected_titles:
        raise ValueError("請至少勾選一個章節。")

    ext = file_type.lower()

    if ext == "pdf":
        data = pdf_extract(file_path, chapters, selected_titles, page_shift)
        return data, "application/pdf"

    elif ext in ("docx", "doc"):
        data = extract_chapters_docx(file_path, chapters, selected_titles)
        return data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    elif ext == "txt":
        data = extract_chapters_txt(file_path, chapters, selected_titles)
        return data, "text/plain; charset=utf-8"

    else:
        raise ValueError(f"不支援的檔案格式：{ext}")
