# Chapter Splitter Tool 🚀

智能章節拆分工具，支援 PDF、DOCX、TXT。  
UI 設計遵循 **The Precision Curator** 設計系統（Apple 風格、卡片式佈局）。

## 🌐 試玩連結 (Live Demo)
可以透過以下連結直接使用本工具：
- [Gradio Live Demo](YOUR_HUGGINGFACE_SPACE_OR_GRADIO_URL_HERE)


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
```

### 2. 啟動應用 (Application)
```bash
python app.py
```
啟動後，瀏覽器將自動開啟 `http://localhost:7860`。

---

## ☁️ 佈署至 Hugging Face Spaces (Deployment)

1. 在 [Hugging Face](https://huggingface.co/new-space) 建立新的 Space。
2. **SDK** 選擇 `Gradio`。
3. 連結你的 **GitHub Repository** 或手動上傳檔案。
4. 確保根目錄包含以下必要檔案：
    - `app.py` (主程式入口)
    - `requirements.txt` (環境依賴)
    - `splitter/` (核心邏輯資料夾)

---

## 📂 專案結構

```bash
.
├── app.py                  # Gradio 主程式
├── splitter/               # 核心偵測與提取邏輯
│   ├── pdf_splitter.py     
│   ├── docx_splitter.py    
│   ├── txt_splitter.py     
│   └── merger.py           
├── requirements.txt        # 套件清單
├── DESIGN.md               # UI 設計規範
└── .gitignore              # 排除版本控制檔案
```

---

## ⚠️ 注意事項

- **PDF**：含有書籤 (TOC) 的檔案效果最佳；不支援純圖片掃描版。
- **DOCX**：建議使用 Word 內建「標題」格式編寫。
- **隱私**：所有檔案處理均在伺服器端完成，處理後建議重新發布以清理快取。

---

## 🎨 設計系統

詳見 [DESIGN.md](./DESIGN.md)。色彩採用：
- **Primary**: `#0071e3` (Blue)
- **Background**: `#fcf8fb`
- **Surface**: `#ffffff` (Card)
- **Font**: **Inter / Outfit**
