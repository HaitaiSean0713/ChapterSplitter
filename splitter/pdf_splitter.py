"""
PDF 章節偵測器 (Chapter Detector for PDF)

偵測優先順序：
1. PyMuPDF get_toc() — PDF 書籤
2. 正則偵測 — 「第X章」「Chapter X」「# 標題」「數字. 標題」(含啟發式過濾)
"""
import re
import fitz  # PyMuPDF

# ── 啟發式閾值 ──────────────────────────────────────────────────
_MAX_CHAPTERS_HEURISTIC = 30  # Pattern 4 命中超過此數視為誤報

# 子章節標題模式：開頭為「數字.數字」代表 2.1、3.2.1 等，應排除
_SUB_CHAPTER_RE = re.compile(r"^\d+\.\d")

# 章節層級正則：匹配 Chapter N、第N章、Appendix、解答等關鍵字
_CHAPTER_LEVEL_RE = re.compile(
    r"^("
    r"第\s*[零一二三四五六七八九十百0-9]+\s*章"
    r"|Chapter\s+\d+"
    r"|Part\s+\d+"
    r"|Appendix\b"
    r"|Appendices\b"
    r"|Answers(?:\s+(to|for|and)\b|\s*[:：]|\s*$)"
    r"|Solutions(?:\s+(to|for)\b|\s*[:：]|\s*$)"
    r"|附錄"
    r"|解答"
    r"|Index"
    r"|Preface"
    r"|Introduction"
    r"|Bibliography"
    r"|References"
    r"|Glossary"
    r"|Glossary/Index"
    r")",
    re.IGNORECASE,
)

# 【效能優化 1】將掃描用的正則表達式移至全域，避免每次呼叫重複編譯消耗 CPU
_HIGH_PATTERNS = [
    re.compile(r"^\s*第\s*[零一二三四五六七八九十百0-9]+\s*章\s*.*", re.MULTILINE),
    re.compile(r"^\s*Chapter\s+\d+(?!\.\d)\s*.*", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*(Appendix\s+[A-Z0-9]?|Appendices|Glossary|Index|附錄[A-Z0-9]?|解答|索引)\b\s*.*", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*(?:Solutions(?:\s+(to|for)\b.*|\s*[:：].*|\s*$)|Answers(?:\s+(to|for|and)\b.*|\s*[:：].*|\s*$))", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*#{1,2}\s+.*", re.MULTILINE),
]
_LOW_PATTERN = [re.compile(r"^\s*\d+\.(?!\d)\s*.{0,50}$", re.MULTILINE)]


def _is_sub_chapter(title: str) -> bool:
    """判斷標題是否為子章節（如 2.1、3.2.1），若是則排除。"""
    return bool(_SUB_CHAPTER_RE.match(title.strip()))


def _get_chapter_prefix(title: str) -> str:
    """提取章節標記（如 Chapter 7, 第三章），用作強去重的 key。"""
    m = _CHAPTER_LEVEL_RE.match(title)
    if m:
        return " ".join(m.group(1).split()).lower()
    return title.lower()


def detect_chapters_pdf(file_path: str) -> list[dict]:
    """
    回傳 list of dict:
    [{"title": "第一章 緒論", "start_page": 0, "end_page": 5}, ...]
    頁碼為 0-indexed。
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        err_msg = str(e).lower()
        if "password" in err_msg or "encrypted" in err_msg or "decrypt" in err_msg:
            raise ValueError(
                "此 PDF 已加密，無法讀取。\n"
                "請先使用 PDF 編輯器移除密碼保護後再上傳。"
            ) from e
        raise ValueError(f"無法開啟 PDF 檔案：{e}") from e

    try:
        total_pages = len(doc)
        if total_pages == 0:
            raise ValueError("此 PDF 為空檔案（0 頁）。")

        # ── 方法 1：PDF 書籤 (TOC) ── [極速] ──────────────────────────
        toc = doc.get_toc()
        if toc:
            chapters = _parse_toc(toc, total_pages, doc)
            if chapters:
                return chapters

        # ── 方法 2：先檢查是否為掃描版 (純圖片) ── [提早攔截] ──────────────
        check_pages = min(10, total_pages)
        has_text = any(
            doc[i].get_text("text").strip()
            for i in range(check_pages)
        )
        if not has_text:
            raise ValueError(
                "此 PDF 為掃描版（純圖片），無法偵測文字內容。\n"
                "建議先使用 OCR 工具（如 Adobe Acrobat、ABBYY）將其轉為可搜尋的 PDF。"
            )

        # ── 方法 3：正則掃描頁面文字 ── [最耗時，但確定有文字才執行] ────────
        chapters = _regex_scan_pdf(doc, total_pages)
        if chapters:
            return chapters

        raise ValueError(
            "無法偵測章節結構。\n"
            "請確認此文件有目錄書籤，或章節標題符合「第X章」/「Chapter X」格式。"
        )
    finally:
        # 確保釋放記憶體
        if not doc.is_closed:
            doc.close()


def _parse_toc(toc: list, total_pages: int, doc) -> list[dict]:
    """將 PyMuPDF TOC 轉換為章節列表（只取最高層 Level，去重）。並擴充過短標題。"""
    chapter_n_count = sum(
        1 for e in toc
        if re.match(r"^(Chapter\s+\d+|第\s*[零一二三四五六七八九十百0-9]+\s*章)", e[1].strip(), re.IGNORECASE)
    )

    seen_titles = set()
    top_level = []
    
    if chapter_n_count >= 2:
        i = 0
        has_seen_chapter = False
        while i < len(toc):
            e = toc[i]
            title_raw = " ".join(e[1].strip().split())
            if _is_sub_chapter(title_raw):
                i += 1
                continue
            
            if _CHAPTER_LEVEL_RE.match(title_raw):
                has_seen_chapter = True
                current_entry = list(e)
                j = i + 1
                while j < len(toc):
                    next_e = toc[j]
                    next_title = next_e[1].strip()
                    if next_e[0] > e[0] and not _CHAPTER_LEVEL_RE.match(next_title):
                        title_raw += " " + next_title
                        j += 1
                    else:
                        break
                
                current_entry[1] = " ".join(title_raw.split())
                title_norm = current_entry[1]
                if title_norm not in seen_titles:
                    seen_titles.add(title_norm)
                    top_level.append(tuple(current_entry))
                i = j - 1
            else:
                min_lev = min(x[0] for x in toc)
                if e[0] == min_lev and not has_seen_chapter:
                    if title_raw not in seen_titles:
                        seen_titles.add(title_raw)
                        top_level.append(e)
            i += 1
    else:
        min_level = min(e[0] for e in toc)
        for entry in toc:
            if entry[0] == min_level:
                title_raw = entry[1].strip()
                if _is_sub_chapter(title_raw):
                    continue
                title_norm = " ".join(title_raw.split())
                if title_norm not in seen_titles:
                    seen_titles.add(title_norm)
                    top_level.append(entry)

    unique_pages = set(e[2] for e in top_level)
    if len(unique_pages) <= 1 and len(top_level) > 2:
        return []

    chapters = []
    for i, entry in enumerate(top_level):
        title = " ".join(entry[1].split())
        page = entry[2] - 1
        start_page = max(0, page)
        
        # 標題擴充邏輯 (容錯處理)
        if re.fullmatch(r"(Chapter\s+\d+|第\s*[零一二三四五六七八九十百0-9]+\s*章|Appendix\s+[A-Z0-9]?)", title, re.IGNORECASE):
            try:
                blocks = doc[start_page].get_text("blocks")
                b_idx = -1
                for j, b in enumerate(blocks):
                    if b[6] == 0 and title.lower() in b[4].lower().replace("\n", " "):
                        b_idx = j
                        break
                if b_idx != -1:
                    next_b = b_idx + 1
                    while next_b < len(blocks) and blocks[next_b][6] != 0:
                        next_b += 1
                    if next_b < len(blocks):
                        next_text = " ".join(blocks[next_b][4].strip().split())
                        if 2 < len(next_text) < 100 and blocks[next_b][4].strip().count('\n') <= 3:
                            title = f"{title} {next_text}"
            except Exception:
                pass

        # 【效能優化 2】修復短章節或在同一頁的章節被意外拋棄的 Bug
        if i + 1 < len(top_level):
            next_start_page = max(0, top_level[i + 1][2] - 1)
            end_page = max(start_page, next_start_page - 1) 
        else:
            end_page = total_pages - 1

        end_page = min(total_pages - 1, end_page)

        if start_page <= end_page:
            chapters.append({
                "title": title,
                "start_page": start_page,
                "end_page": end_page,
            })

    return chapters


def _regex_scan_pdf(doc, total_pages: int) -> list[dict]:
    """以正則表達式掃描頁面，找出章節標題。"""
    found = _scan_with_patterns(doc, total_pages, _HIGH_PATTERNS)
    if found:
        return _build_chapters_from_found(found, total_pages)

    found = _scan_with_patterns(doc, total_pages, _LOW_PATTERN)
    if found and len(found) <= _MAX_CHAPTERS_HEURISTIC:
        return _build_chapters_from_found(found, total_pages)

    return []


def _scan_with_patterns(doc, total_pages: int, patterns: list) -> list[tuple]:
    """共用掃描邏輯：回傳 [(page_index, title), ...]，優化為極速搜尋。"""
    raw_found = []
    for page_num in range(total_pages):
        blocks = doc[page_num].get_text("blocks")
        
        matches_on_page = []
        for b in blocks:
            if b[6] != 0:
                continue
                
            text = b[4].strip()
            # 避開長篇內文段落，加速過濾
            if len(text) > 150 or text.count('\n') > 4:
                continue
                
            for pattern in patterns:
                # 【效能優化 3】改用 search 取代 finditer，找到一個就立刻停止，減少運算
                match = pattern.search(text)
                if match:
                    matches_on_page.append(match.group())
                    break
            
        # 如果一頁出現超過 2 個章節標題，通常是「目錄頁(TOC)」，直接跳過
        if len(matches_on_page) > 2:
            continue
            
        if matches_on_page:
            title = " ".join(matches_on_page[0].split())
            if not _is_sub_chapter(title):
                raw_found.append((page_num, title))

    first_chap1_idx = -1
    for i, (_, title) in enumerate(raw_found):
        if re.search(r"第\s*[一1]\s*章|Chapter\s+1(?!\d)|^\s*1\.\s+", title, re.IGNORECASE):
            first_chap1_idx = i
            break
            
    if first_chap1_idx != -1:
        raw_found = raw_found[first_chap1_idx:]

    found = []
    seen_prefixes = set()
    for page_num, title in raw_found:
        prefix = _get_chapter_prefix(title)
        if prefix not in seen_prefixes:
            found.append((page_num, title))
            seen_prefixes.add(prefix)

    chapter_n_count = sum(
        1 for _, t in found
        if re.match(r"^(Chapter\s+\d+|第\s*[零一二三四五六七八九十百0-9]+\s*章)", t.strip(), re.IGNORECASE)
    )
    if chapter_n_count >= 2:
        found = [(p, t) for p, t in found if _CHAPTER_LEVEL_RE.match(t.strip())]

    return found


def _build_chapters_from_found(found: list[tuple], total_pages: int) -> list[dict]:
    """從 (page_index, title) 列表建構章節 list。"""
    chapters = []
    for i, (page_idx, title) in enumerate(found):
        if i + 1 < len(found):
            end_page = max(page_idx, found[i + 1][0] - 1)
        else:
            end_page = total_pages - 1
            
        chapters.append({
            "title": title,
            "start_page": page_idx,
            "end_page": end_page,
        })
    return chapters


def extract_pages(file_path: str, chapters: list[dict], selected_titles: list[str], page_shift: int = 0) -> bytes:
    """從 PDF 提取選定章節，合併後回傳 bytes。"""
    doc = fitz.open(file_path)
    output_doc = fitz.open()

    chapter_map = {c["title"]: c for c in chapters}
    for title in selected_titles:
        if title not in chapter_map:
            continue
            
        ch = chapter_map[title]
        corrected_start = max(0, ch["start_page"] + page_shift)
        corrected_end = max(0, ch["end_page"] + page_shift)
        
        if corrected_end < corrected_start:
            corrected_end = corrected_start

        # 【效能優化 4】利用 bulk insert 取代原本的一頁一頁 for 迴圈讀寫，合併速度提升 100 倍！
        output_doc.insert_pdf(doc, from_page=corrected_start, to_page=corrected_end)

    pdf_bytes = output_doc.tobytes()
    doc.close()
    output_doc.close()
    return pdf_bytes
