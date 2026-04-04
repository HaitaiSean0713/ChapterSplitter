"""
TXT 章節偵測器 (Chapter Detector for plain text)

正則偵測：
- 「第X章」「Chapter X」「# 標題」
- 「數字. 標題」（含空白行前置檢查，降低誤報）
"""
import re
import io

# ── 啟發式閾值 ──────────────────────────────────────────────────
_MAX_CHAPTERS_HEURISTIC = 30

# 子章節標題模式：開頭為「數字.數字」用於排除 2.1、3.2 等
_SUB_CHAPTER_RE = re.compile(r"^\d+\.\d")


def _is_sub_chapter(title: str) -> bool:
    return bool(_SUB_CHAPTER_RE.match(title.strip()))

def _get_chapter_prefix(title: str) -> str:
    m = re.match(r"^(第\s*[零一二三四五六七八九十百0-9]+\s*章|Chapter\s+\d+|#{1,2}\s+\d+|\d+\.|Appendix\s+[A-Z0-9]?|Appendices|Solutions|Answers|附錄[A-Z0-9]?|解答)", title, re.IGNORECASE)
    if m:
        return " ".join(m.group(1).split()).lower()
    return title.lower()

def _filter_and_dedup(found: list[tuple]) -> list[tuple]:
    # 尋找 Chapter 1 並捨棄之前的
    first_chap1_idx = -1
    for i, (_, title) in enumerate(found):
        if re.search(r"第\s*[一1]\s*章|Chapter\s+1(?!\d)|^\s*1\.\s+", title, re.IGNORECASE):
            first_chap1_idx = i
            break
            
    if first_chap1_idx != -1:
        found = found[first_chap1_idx:]

    # 依 prefix 去重
    new_found = []
    seen_prefixes = set()
    for item in found:
        prefix = _get_chapter_prefix(item[1])
        if prefix not in seen_prefixes:
            new_found.append(item)
            seen_prefixes.add(prefix)
            
    return new_found


def detect_chapters_txt(file_path: str) -> list[dict]:
    """
    回傳 list of dict:
    [{"title": "第一章 前言", "start_line": 0, "end_line": 42}, ...]
    行號為 0-indexed。
    """
    # 使用 utf-8-sig 自動處理 BOM 前綴
    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        lines = f.readlines()

    total = len(lines)
    if total == 0:
        raise ValueError("此文字檔為空檔案。")

    # ── 高精確度 Pattern ─────────────────────────────────────────
    HIGH_PATTERNS = [
        re.compile(r"^第\s*[零一二三四五六七八九十百0-9]+\s*章\s*.*"),
        re.compile(r"^Chapter\s+\d+(?!\.\d)\s*.*", re.IGNORECASE),
        re.compile(r"^(Appendix\s+[A-Z0-9]?|Appendices|附錄[A-Z0-9]?|解答)\b\s*.*", re.IGNORECASE),
        re.compile(r"^(Solutions|Answers)(?:\s+(to|for|and)\b.*|\s*[:：].*|\s*)$", re.IGNORECASE),
        re.compile(r"^#{1,2}\s+.*"),
    ]

    found = _scan_lines(lines, HIGH_PATTERNS)
    if found:
        return _build_chapters(found, total)

    # ── 低精確度 Pattern（數字編號） ──────────────────────────────
    LOW_PATTERN = re.compile(r"^\d+\.(?!\d)\s*.{0,50}$")

    found = _scan_lines_with_blank_check(lines, LOW_PATTERN)
    if found and len(found) <= _MAX_CHAPTERS_HEURISTIC:
        return _build_chapters(found, total)

    raise ValueError(
        "無法偵測章節結構。\n"
        "請確認文字檔的章節標題符合「第X章」/「Chapter X」/「# 標題」格式。"
    )


def _scan_lines(lines: list[str], patterns: list) -> list[tuple]:
    """高精確度掃描：逐行比對 Pattern，命中即收錄。"""
    found = []
    seen_titles = set()
    for i, line in enumerate(lines):
        text = line.strip()
        if not text or _is_sub_chapter(text):
            continue
        if text in seen_titles:
            continue
        for p in patterns:
            if p.match(text):
                found.append((i, text))
                seen_titles.add(text)
                break
    return found


def _scan_lines_with_blank_check(lines: list[str], pattern) -> list[tuple]:
    """
    低精確度掃描：要求匹配行的前一行或前兩行為空白行，
    以過濾掉列表項目等誤報。
    """
    found = []
    seen_titles = set()
    for i, line in enumerate(lines):
        text = line.strip()
        if not text or _is_sub_chapter(text):
            continue
        if text in seen_titles:
            continue
        if not pattern.match(text):
            continue
        # 檢查前方是否有空白行間隔（章節標題通常前方有留白）
        added = False
        if i == 0:
            # 第一行直接收錄
            found.append((i, text))
            added = True
        elif i >= 1 and not lines[i - 1].strip():
            found.append((i, text))
            added = True
        elif i >= 2 and not lines[i - 2].strip():
            found.append((i, text))
            added = True
            
        if added:
            seen_titles.add(text)
    return found


def _build_chapters(found: list[tuple], total: int) -> list[dict]:
    """從 (line_index, title) 列表建構章節 list。"""
    found = _filter_and_dedup(found)
    chapters = []
    for idx, (line_idx, title) in enumerate(found):
        if idx + 1 < len(found):
            end_line = found[idx + 1][0] - 1
        else:
            end_line = total - 1
        chapters.append({
            "title": title,
            "start_line": line_idx,
            "end_line": end_line,
        })
    return chapters


def extract_chapters_txt(file_path: str, chapters: list[dict], selected_titles: list[str]) -> bytes:
    """提取選定章節，合併後回傳 bytes (UTF-8)。"""
    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        lines = f.readlines()

    chapter_map = {c["title"]: c for c in chapters}
    result_lines = []

    for title in selected_titles:
        if title not in chapter_map:
            continue
        ch = chapter_map[title]
        if result_lines:
            result_lines.append("\n\n")
        result_lines.extend(lines[ch["start_line"]: ch["end_line"] + 1])

    return "".join(result_lines).encode("utf-8")
