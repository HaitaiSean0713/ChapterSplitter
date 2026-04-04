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


def _is_sub_chapter(title: str) -> bool:
    """判斷標題是否為子章節（如 2.1、3.2.1），若是則排除。"""
    t = title.strip()
    return bool(_SUB_CHAPTER_RE.match(t))


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

    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValueError("此 PDF 為空檔案（0 頁）。")

    # ── 方法 1：PDF 書籤 (TOC) ──────────────────────────────────
    toc = doc.get_toc()
    if toc:
        print("[DEBUG] TOC raw entries:")
        for i, e in enumerate(toc):
            print(f"  [{i}] level={e[0]}, title={e[1]!r}, page={e[2]}")
        chapters = _parse_toc(toc, total_pages, doc)
        if chapters:
            doc.close()
            return chapters
        # TOC 存在但解析結果為空（例如全部指向同一頁）→ Fallback

    # ── 方法 2：正則掃描頁面文字 ─────────────────────────────────
    chapters = _regex_scan_pdf(doc, total_pages)
    doc.close()
    if chapters:
        return chapters

    # ── 方法 3：檢查是否為掃描版 ─────────────────────────────────
    # 重新開啟檢查前幾頁是否有文字
    doc2 = fitz.open(file_path)
    has_text = any(
        doc2[i].get_text("text").strip()
        for i in range(min(5, total_pages))
    )
    doc2.close()

    if not has_text:
        raise ValueError(
            "此 PDF 為掃描版（純圖片），無法偵測文字內容。\n"
            "建議先使用 OCR 工具（如 Adobe Acrobat、ABBYY）將其轉為可搜尋的 PDF。"
        )

    raise ValueError(
        "無法偵測章節結構。\n"
        "請確認此文件有目錄書籤，或章節標題符合「第X章」/「Chapter X」/「# 標題」格式。"
    )


def _parse_toc(toc: list, total_pages: int, doc) -> list[dict]:
    """將 PyMuPDF TOC 轉換為章節列表（只取最高層 Level，去重）。並擴充過短標題。"""
    # 計算有多少條目符合 "Chapter N" 模式
    chapter_n_count = sum(
        1 for e in toc
        if re.match(r"^(Chapter\s+\d+|第\s*[零一二三四五六七八九十百0-9]+\s*章)", e[1].strip(), re.IGNORECASE)
    )

    seen_titles = set()
    top_level = []
    
    if chapter_n_count >= 2:
        # 教科書模式：合併標籤與標題 (例如 "Chapter 10" 與下層 "Title Name")
        i = 0
        has_seen_chapter = False
        while i < len(toc):
            e = toc[i]
            title_raw = " ".join(e[1].strip().split())
            if _is_sub_chapter(title_raw):
                i += 1
                continue
            
            # 如果匹配章節關鍵字 (如 Chapter 10)
            if _CHAPTER_LEVEL_RE.match(title_raw):
                has_seen_chapter = True
                current_entry = list(e)
                # 為了捕捉多層合併 (如 Chapter 10 \n Title)，嘗試看下一條目是否應併入
                j = i + 1
                while j < len(toc):
                    next_e = toc[j]
                    next_title = next_e[1].strip()
                    # 若為更深層級，且不匹配新的章節編號
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
                i = j - 1 # 跳過已合併項目
            else:
                # 非 Chapter N 關鍵字但屬極淺層級 (如 Preface, Index)
                min_lev = min(e[0] for e in toc)
                if e[0] == min_lev and not has_seen_chapter:
                    if title_raw not in seen_titles:
                        seen_titles.add(title_raw)
                        top_level.append(e)
            i += 1
    else:
        # 傳統模式：取 min_level
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

    # ── 異常偵測：所有書籤指向同一頁 ────────────────────────────
    unique_pages = set(e[2] for e in top_level)
    if len(unique_pages) <= 1 and len(top_level) > 2:
        return []

    chapters = []
    for i, entry in enumerate(top_level):
        title = " ".join(entry[1].split())  # normalize 換行 / 多餘空白
        page = entry[2] - 1  # 轉 0-indexed
        start_page = max(0, page)
        
        # 標題過短擴充邏輯 (補足像 "Chapter 10" 這樣缺少副標題的項目)
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
                        # 避免抓到長篇內文或頁碼數字
                        if 2 < len(next_text) < 100 and blocks[next_b][4].strip().count('\n') <= 3:
                            title = f"{title} {next_text}"
            except Exception:
                pass

        if i + 1 < len(top_level):
            end_page = top_level[i + 1][2] - 2
        else:
            end_page = total_pages - 1

        start_page = max(0, page)
        end_page = min(total_pages - 1, end_page)

        if start_page <= end_page:
            chapters.append({
                "title": title,
                "start_page": start_page,
                "end_page": end_page,
            })

    return chapters


def _regex_scan_pdf(doc, total_pages: int) -> list[dict]:
    """以正則表達式掃描頁面，找出章節標題。含啟發式過濾。"""
    # 高精確度 Pattern（1~3）
    HIGH_PATTERNS = [
        re.compile(r"^\s*第\s*[零一二三四五六七八九十百0-9]+\s*章\s*.*", re.MULTILINE),
        re.compile(r"^\s*Chapter\s+\d+(?!\.\d)\s*.*", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^\s*(Appendix\s+[A-Z0-9]?|Appendices|Glossary|Index|附錄[A-Z0-9]?|解答|索引)\b\s*.*", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^\s*(?:Solutions(?:\s+(to|for)\b.*|\s*[:：].*|\s*$)|Answers(?:\s+(to|for|and)\b.*|\s*[:：].*|\s*$))", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^\s*#{1,2}\s+.*", re.MULTILINE),
    ]
    # 低精確度 Pattern（4）— 需啟發式過濾；排除 2.1 等子章節
    LOW_PATTERN = re.compile(r"^\s*\d+\.(?!\d)\s*.{0,50}$", re.MULTILINE)

    # 先用高精確度 Pattern 掃描
    found = _scan_with_patterns(doc, total_pages, HIGH_PATTERNS)
    if found:
        return _build_chapters_from_found(found, total_pages)

    # 高精確度無結果 → 嘗試低精確度 Pattern
    found = _scan_with_patterns(doc, total_pages, [LOW_PATTERN])
    if found and len(found) <= _MAX_CHAPTERS_HEURISTIC:
        return _build_chapters_from_found(found, total_pages)

    # 命中數超過閾值 → 視為誤報，放棄
    return []


def _scan_with_patterns(doc, total_pages: int, patterns: list) -> list[tuple]:
    """共用掃描邏輯：回傳 [(page_index, title), ...]，只取首個命中。"""
    raw_found = []
    for page_num in range(total_pages):
        blocks = doc[page_num].get_text("blocks")
        
        matches_on_page = []
        for b in blocks:
            # block type 0 代表文字
            if b[6] != 0:
                continue
                
            text = b[4]
            # 避開長篇大論的內文段落 (Paragraph) 
            # 真正的章節標題通常長度短 (<150字元)，且行數少 (換行次數 <= 4)
            if len(text.strip()) > 150 or text.count('\n') > 4:
                continue
                
            for pattern in patterns:
                # 這裡改用 finditer 是因為可能一個 block 剛好有兩個命中，但在這長度下極少見
                matches = list(pattern.finditer(text))
                if matches:
                    matches_on_page.extend(matches)
                    break
            
        if len(matches_on_page) > 2:
            continue
            
        # 若單頁符合數量正常，取第一個命中的當作該頁章節
        if matches_on_page:
            raw = matches_on_page[0].group().strip()
            title = " ".join(raw.split())
            if not _is_sub_chapter(title):
                raw_found.append((page_num, title))

    # 尋找 Chapter 1（或第一章），並捨棄在此之前出現的（例如在 Preface 舉例的 Chapter 2）
    first_chap1_idx = -1
    for i, (_, title) in enumerate(raw_found):
        if re.search(r"第\s*[一1]\s*章|Chapter\s+1(?!\d)|^\s*1\.\s+", title, re.IGNORECASE):
            first_chap1_idx = i
            break
            
    if first_chap1_idx != -1:
        raw_found = raw_found[first_chap1_idx:]

    # 依 prefix 去重（解決真正的 Chapter 7 之後，解答頁面又出現 Chapter 7 的問題）
    found = []
    seen_prefixes = set()
    for page_num, title in raw_found:
        prefix = _get_chapter_prefix(title)
        if prefix not in seen_prefixes:
            found.append((page_num, title))
            seen_prefixes.add(prefix)

    # ── 章節級別過濾：有 Chapter N 時排除非章節條目 ──────────────
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
            end_page = found[i + 1][0] - 1
        else:
            end_page = total_pages - 1
        chapters.append({
            "title": title,
            "start_page": page_idx,
            "end_page": end_page,
        })
    return chapters


def extract_pages(file_path: str, chapters: list[dict], selected_titles: list[str], page_shift: int = 0) -> bytes:
    """
    從 PDF 提取選定章節，合併後回傳 bytes。
    page_shift 用於微調章節擷取範圍，例如若遇到封面在前一頁，可設定 -1 或是由使用者在前端決定。
    """
    doc = fitz.open(file_path)
    output_doc = fitz.open()

    chapter_map = {c["title"]: c for c in chapters}
    for title in selected_titles:
        if title not in chapter_map:
            continue
        ch = chapter_map[title]
        # 依使用者傳入之平移參數決定起始與結束頁
        corrected_start = max(0, ch["start_page"] + page_shift)
        corrected_end = max(0, ch["end_page"] + page_shift)
        
        if corrected_end < corrected_start:
            corrected_end = corrected_start

        for page_num in range(corrected_start, corrected_end + 1):
            output_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

    pdf_bytes = output_doc.tobytes()
    doc.close()
    output_doc.close()
    return pdf_bytes
