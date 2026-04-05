---
title: Chapter Splitter
emoji: ✂️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# Chapter Splitter Tool 🚀

智能章節拆分工具，支援 PDF、DOCX、TXT。  
UI 設計遵循 **The Precision Curator** 設計系統（Apple 風格、卡片式佈局）。

## 🌐 試玩連結 (Live Demo)
可以透過以下連結直接使用本工具：
- [Gradio Live Demo](https://huggingface.co/spaces/haitai0713/ChapterSplitter)


---

## 🌟 功能特點

- **多格式支援**：精準偵測 PDF、DOCX 及 TXT 檔案的章節。
- **智能偵測**：優先讀取 PDF 書籤，並輔以正則表達式 (Regex) 掃描。
- **彈性合併**：自選章節並合併為單一檔案下載。
- **現代化介面**：使用 Gradio 打造，具備響應式設計與流暢動畫。

---

## 🛠️ 安裝與啟動

### 1. 安裝依賴 (Dependencies)
```bash
pip install -r requirements.txt
