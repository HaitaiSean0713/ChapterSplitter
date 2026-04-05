"""
Chapter Splitter Tool -- Gradio App
Dark Mode Edition
"""
import os
import tempfile
import gradio as gr
import re
import fitz  # 這是 PyMuPDF 的套件名稱

from splitter.pdf_splitter import detect_chapters_pdf
from splitter.docx_splitter import detect_chapters_docx
from splitter.txt_splitter import detect_chapters_txt
from splitter.merger import merge_selected

# -- Global state -------------------------------------------------------
_chapters: list[dict] = []
_file_path: str = ""
_file_type: str = ""

EXT_MAP = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".txt": "txt",
    ".md": "txt",
}

# -- Design Tokens (Dark Mode) ------------------------------------------
HEAD = """
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script>
// 等待 Tailwind 載入後再設定 config
(function initTailwind() {
    if (typeof tailwind !== 'undefined' && tailwind.config) {
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    colors: {
                        "primary-container": "#4da3ff",
                        "primary": "#82c0ff",
                        "surface": "#111318",
                        "on-surface": "#e3e2e6",
                        "secondary": "#9ab4d4",
                        "surface-container-low": "#1e2128",
                        "surface-container-lowest": "#191c23"
                    },
                    fontFamily: {
                        headline: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
                        body: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"]
                    }
                }
            }
        };
        console.log('✅ Tailwind config 設定完成');
    } else {
        setTimeout(initTailwind, 50);
    }
})();
</script>
"""

CSS = """
body, .gradio-container {
    background-color: #111318 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif !important;
    color: #e3e2e6 !important;
}

[class*="max-w-"] { width: 100% !important; margin: 0 auto !important; }
.fixed { position: fixed !important; }

.apple-shadow {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4) !important;
}
.glass-header {
    background-color: rgba(17, 19, 24, 0.85) !important;
    backdrop-filter: blur(20px) !important;
}
.glass-nav {
    background-color: rgba(17, 19, 24, 0.85) !important;
    backdrop-filter: blur(20px) !important;
}
.gradio-container {
    padding: 0 !important;
    max-width: 100% !important;
}
#main-app { padding: 0 !important; }

/* Upload zone */
#upload-zone {
    background: #191c23 !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.4) !important;
    position: relative !important;
    overflow: hidden !important;
    border-radius: 16px !important;
}

#upload-zone .upload-container {
    border: none !important;
    background: transparent !important;
}

.gradio-container .file-preview,
.gradio-container label.block {
    color: #9ab4d4 !important;
}

/* Chapter checkboxes */
#chapter-list {
    background: transparent !important;
    border: none !important;
    gap: 8px !important;
    display: flex !important;
    flex-direction: column !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}

#chapter-list label {
    background: #191c23 !important;
    border-radius: 8px !important;
    padding: 20px !important;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
    transition: all 0.2s !important;
    display: flex !important;
    align-items: center !important;
    border: none !important;
    width: 100% !important;
    cursor: pointer !important;
}

#chapter-list label:hover {
    transform: scale(1.01) !important;
    background: #22273a !important;
}

#chapter-list label:has(input:checked) {
    background: #0f1e36 !important;
    border-left: 3px solid #4da3ff !important;
}

#chapter-list input[type="checkbox"] {
    appearance: none;
    -webkit-appearance: none;
    width: 22px !important;
    height: 22px !important;
    border-radius: 50% !important;
    border: 1.5px solid #3a3d4a !important;
    background: #1e2128 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-right: 16px !important;
    transition: all 0.2s ease !important;
    flex-shrink: 0 !important;
}

#chapter-list input[type="checkbox"]:checked {
    background-color: #4da3ff !important;
    border-color: #4da3ff !important;
}

#chapter-list input[type="checkbox"]:checked::after {
    content: '✓' !important;
    font-size: 14px !important;
    color: #111318 !important;
    font-weight: bold !important;
}

#chapter-list span {
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #e3e2e6 !important;
}

#status-selected span {
    font-size: 13px !important;
    color: #9ab4d4 !important;
}

/* Buttons */
#btn-detect button, #btn-merge button {
    background: #1a4a8a !important;
    color: #82c0ff !important;
    font-size: 16px !important;
}

#btn-download button {
    background: #1a4d2a !important;
    color: #34d058 !important;
    font-size: 16px !important;
}

#btn-reset button {
    background: #1e2128 !important;
    color: #e3e2e6 !important;
    font-size: 15px !important;
}

#btn-select-all button, #btn-clear-all button {
    color: #4da3ff !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.gradio-container input[type=range] {
    accent-color: #4da3ff !important;
}

section span {
    color: #e3e2e6 !important;
}

/* Layout fixes */
#main-content-area {
    padding-bottom: 40px !important;
}

#bottom-action-bar {
    background: transparent !important;
    border-top: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

#bottom-inner {
    padding: 0 !important;
}

footer {
    display: none !important;
}

/* ✅ 修正：移除對 .wrap 和 .main 的 display: block 強制覆寫 */
body, #root, .gradio-container {
    min-height: fit-content !important; 
    height: auto !important;
    display: block !important;
}

.gradio-container {
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
}
/* ✅ 修正：Gradio 實際使用的進度條 Class */
.progress-text {
    color: #e3e2e6 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    z-index: 100 !important;
}

.progress-level {
    background: linear-gradient(90deg, #4da3ff, #82c0ff) !important;
}

/* 確保進度條容器在深色模式下的背景 */
.wrap > div[class*="progress"] {
    background: rgba(30, 33, 40, 0.9) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
}
"""

def _get_ext(path):
    _, ext = os.path.splitext(path)
    return ext.lower()

def detect_chapters(file_obj, progress=gr.Progress()): 
    """偵測章節（帶進度條）"""
    global _chapters, _file_path, _file_type

    if file_obj is None:
        yield (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(choices=[], value=[]),
            gr.update(value='<p style="color:#ff6b6b;text-align:center;margin-top:8px;font-size:13px;font-weight:700;">❌ 請加上檔案</p>', visible=True),
            gr.update(value="")
        )
        return
    
    # Step 1: 讀取檔案
    progress(0, desc="📂 正在讀取檔案...")
    
    path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    ext = _get_ext(path)
    file_type = EXT_MAP.get(ext)

    if file_type is None:
        yield (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(choices=[], value=[]),
            gr.update(value=f'<p style="color:#ff6b6b;text-align:center;font-size:13px;font-weight:700;">❌ 不支援的格式「{ext}」</p>', visible=True),
            gr.update(value="")
        )
        return
        
    try:
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        
        # Step 2: 分析檔案
        progress(0.2, desc=f"🔍 正在分析 {file_type.upper()} 檔案...")
        yield (gr.update(), gr.update(), gr.update(), gr.update(), gr.update())  # 推送進度

        
        if file_type == "pdf":
            progress(0.4, desc="📖 偵測 PDF 章節...")
            yield (gr.update(), gr.update(), gr.update(), gr.update(), gr.update())  # 推送進度

            chapters = detect_chapters_pdf(path)
        elif file_type == "docx":
            progress(0.4, desc="📄 偵測 Word 章節...")
            yield (gr.update(), gr.update(), gr.update(), gr.update(), gr.update())  # 推送進度
            chapters = detect_chapters_docx(path)
        else:
            progress(0.4, desc="📝 偵測文字章節...")
            yield (gr.update(), gr.update(), gr.update(), gr.update(), gr.update())  # 推送進度
            chapters = detect_chapters_txt(path)

        # Step 3: 完成
        progress(1.0, desc="✅ 偵測完成！")
        
        _chapters = chapters
        _file_path = path
        _file_type = file_type

        labeled = [f"{i+1}. {c['title']}" for i, c in enumerate(chapters)]

        stats_html = f'''
        <div style="background:#191c23;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.4);padding:24px;display:flex;flex-direction:column;gap:16px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <span style="font-size:17px;font-weight:700;color:#e3e2e6;">📖 偵測完成</span>
                <span style="padding:6px 16px;border-radius:20px;background:#1a3a6e;color:#82c0ff;font-size:13px;font-weight:700;">共 {len(labeled)} 個章節</span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;">
                <div style="background:#1e2128;padding:6px 12px;border-radius:8px;display:flex;align-items:center;gap:6px;">
                    <span style="font-size:12px;color:#9ab4d4;font-weight:500;">📊 檔案大小：{file_size_mb:.1f} MB</span>
                </div>
                <div style="background:#1e2128;padding:6px 12px;border-radius:8px;display:flex;align-items:center;gap:6px;">
                    <span style="font-size:12px;color:#9ab4d4;font-weight:500;">📑 格式：{file_type.upper()}</span>
                </div>
            </div>
        </div>
        '''

        yield (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(choices=labeled, value=labeled),
            gr.update(value="", visible=False),
            gr.update(value=stats_html)
        )
        return

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(choices=[], value=[]),
            gr.update(value=f'<p style="color:#ff6b6b;text-align:center;font-size:13px;font-weight:700;">❌ 發生錯誤：{e}</p>', visible=True),
            gr.update(value="")
        )
        return
        
def select_all():
    global _chapters
    labeled = [f"{i+1}. {c['title']}" for i, c in enumerate(_chapters)]
    return gr.update(value=labeled)

def clear_all():
    return gr.update(value=[])

def update_selection_count(selected):
    global _chapters
    if selected is None:
        selected = []
    return f'<span style="color:#9ab4d4;font-size:13px;font-weight:700;margin-left:auto;padding-right:8px;">已選 {len(selected)} / {len(_chapters)} 章節</span>'

def download_chapters(selected_labels, page_shift, progress=gr.Progress()):
    """下載章節（帶進度條）"""
    global _chapters, _file_path, _file_type

    if not selected_labels:
        yield(
            gr.update(),
            gr.update(value='<p style="color:#ff6b6b;text-align:center;font-size:13px;font-weight:700;">❌ 請至少勾選一個章節。</p>', visible=True)
        )
        return
        
    try:
        # Step 1: 準備合併
        progress(0, desc="📋 正在準備合併...")
        yield (gr.update(), gr.update())  # 推送進度

        
        selected_titles = []
        for label in selected_labels:
            dot_pos = label.index(". ")
            idx = int(label[:dot_pos]) - 1
            selected_titles.append(_chapters[idx]["title"])

        # Step 2: 合併檔案
        progress(0.2, desc=f"🔨 正在合併 {len(selected_titles)} 個章節...")
        yield (gr.update(), gr.update())  # 推送進度

        data, mime = merge_selected(_file_path, _file_type, _chapters, selected_titles, int(page_shift))

        ext_map = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain; charset=utf-8": ".txt",
        }
        suffix = ext_map.get(mime, ".bin")

        # Step 3: PDF 壓縮
        if suffix == ".pdf":
            progress(0.6, desc="🗜️ 正在壓縮 PDF...")
            yield (gr.update(), gr.update())  # 推送進度

            try:
                doc = fitz.open(stream=data, filetype="pdf")
                compressed_data = doc.write(garbage=4, deflate=True)
                doc.close()
                
                original_size_mb = len(data) / (1024 * 1024)
                compressed_size_mb = len(compressed_data) / (1024 * 1024)
                compression_ratio = (1 - compressed_size_mb / original_size_mb) * 100
                
                print(f"✅ PDF 壓縮成功：{original_size_mb:.1f} MB → {compressed_size_mb:.1f} MB (節省 {compression_ratio:.1f}%)")
                data = compressed_data
            except Exception as compress_err:
                print(f"⚠️ 壓縮失敗，使用原始檔案：{compress_err}")

        # Step 4: 儲存檔案
        progress(0.9, desc="💾 正在儲存檔案...")
        yield (gr.update(), gr.update())  # 推送進度

        
        if len(selected_titles) == 1:
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', selected_titles[0][:50]).strip()
            out_filename = f"{safe_title}{suffix}"
        else:
            out_filename = f"Merged_Chapters_{len(selected_titles)}{suffix}"

        out_dir = os.path.abspath("outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, out_filename)
        
        with open(out_path, "wb") as f:
            f.write(data)

        final_size_mb = len(data) / (1024 * 1024)
        
        # Step 5: 完成
        progress(1.0, desc="✅ 合併完成！")

        yield (
            gr.update(value=out_path, visible=True),
            gr.update(
                value=f'<p style="color:#34d058;text-align:center;font-size:13px;font-weight:700;">✓ 合併與壓縮完成！(檔案大小：{final_size_mb:.1f} MB)</p>', 
                visible=True
            )
        )
        return

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield (
            gr.update(visible=False),
            gr.update(value=f'<p style="color:#ff6b6b;text-align:center;font-size:13px;font-weight:700;">❌ 錯誤：{str(e)}</p>', visible=True)
        )
        return

def reset_to_start():
    global _chapters, _file_path, _file_type
    _chapters = []
    _file_path = ""
    _file_type = ""
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(value=None)
    )

# -- UI Construction ----------------------------------------------------

with gr.Blocks(css=CSS, head=HEAD, theme=gr.themes.Default()) as demo:
    with gr.Column(elem_id="screen-start") as screen_start:
        gr.HTML('''
        <header class="w-full glass-nav flex flex-col items-center justify-center py-4 px-6" style="border-bottom:1px solid #2a2d38;">
            <div class="flex flex-col items-center text-center">
                <h1 style="font-size:20px;font-weight:700;color:#e3e2e6;letter-spacing:-0.3px;">章節拆分工具</h1>
                <p style="font-size:14px;font-weight:300;color:#9ab4d4;margin-top:2px;">支援 PDF・Word・Markdown</p>
            </div>
        </header>
        ''')

        with gr.Column(elem_classes="max-w-[640px] mx-auto pt-8 pb-4 px-6 flex flex-col gap-8 w-full"):
            gr.HTML('''
            <section style="background:#1e1a0e;padding:24px;border-radius:16px;display:flex;flex-direction:column;gap:16px;border:1px solid #3a2e00;">
                <div style="display:flex;align-items:center;gap:8px;color:#f5c842;">
                    <span style="font-size:20px;">⚠</span>
                    <h2 style="font-weight:700;color:#f5c842;">使用提醒</h2>
                </div>
                <div style="display:grid;gap:12px;">
                    <div style="display:flex;align-items:flex-start;gap:12px;font-size:14px;color:#b0b8c8;">
                        <span style="color:#34d058;font-size:18px;">✓</span>
                        <span>大學課本 PDF（含目錄書籤）</span>
                    </div>
                    <div style="display:flex;align-items:flex-start;gap:12px;font-size:14px;color:#b0b8c8;">
                        <span style="color:#34d058;font-size:18px;">✓</span>
                        <span>有標題樣式的 Word 文件（.docx）</span>
                    </div>
                    <div style="display:flex;align-items:flex-start;gap:12px;font-size:14px;color:#b0b8c8;">
                        <span style="color:#34d058;font-size:18px;">✓</span>
                        <span>Markdown 文件（.md）</span>
                    </div>
                </div>
            </section>
            ''')

            with gr.Column(elem_classes="p-4 rounded-[16px]"):
                file_upload = gr.File(
                    label="拖曳檔案至此 或點擊上傳",
                    file_types=[".md", ".pdf", ".docx", ".doc", ".txt"],
                    type="filepath",
                    elem_id="upload-zone"
                )
                detect_btn = gr.Button(
                    "🔍 開始偵測章節",
                    elem_id="btn-detect",
                    elem_classes="w-full mt-4 h-[52px] font-bold rounded-[14px] border-none",
                )
                error_msg_start = gr.HTML("", visible=False)

    with gr.Column(elem_id="screen-results", visible=False) as screen_results:
        gr.HTML('''
        <header class="fixed top-0 w-full z-50 glass-header" style="border-bottom:1px solid #2a2d38;box-shadow:0 1px 16px rgba(0,0,0,0.5);">
            <div style="display:flex;align-items:center;padding:0 16px;height:64px;max-width:56rem;margin:0 auto;justify-content:space-between;">
                <h1 style="font-weight:700;font-size:20px;letter-spacing:-0.3px;color:#e3e2e6;margin-left:8px;">章節拆分工具</h1>
            </div>
        </header>
        ''')

        with gr.Column(elem_classes="pt-24 px-4 pb-4 max-w-2xl mx-auto w-full", elem_id="main-content-area"):
            stats_html = gr.HTML("")

            with gr.Row(elem_classes="mb-4 flex flex-row items-center justify-start px-2 mt-4"):
                btn_select_all = gr.Button("全選", elem_id="btn-select-all", elem_classes="bg-transparent shadow-none border-none font-bold text-[15px]", scale=0, min_width=80)                
                btn_clear_all = gr.Button("全取消", elem_id="btn-clear-all", elem_classes="bg-transparent shadow-none border-none font-bold text-[15px]", scale=0, min_width=80)
                status_selected = gr.HTML('<span style="color:#9ab4d4;font-size:13px;font-weight:700;margin-left:auto;padding-right:8px;">已選 0 章節</span>', elem_id="status-selected")

            chapter_checkboxes = gr.CheckboxGroup(label="", choices=[], elem_id="chapter-list", container=False)

            with gr.Column(elem_classes="mt-8 mb-0 w-full", elem_id="bottom-action-bar"):
                with gr.Column(elem_classes="w-full", elem_id="bottom-inner"):
                    page_shift_slider = gr.Slider(
                        minimum=-2, maximum=2, step=1, value=-1,
                        label="封面頁校正 (預設 -1 頁)",
                        elem_classes="mb-3"
                    )
                    btn_merge = gr.Button(
                        "🔨 開始合併已選章節",
                        elem_id="btn-merge",
                        elem_classes="w-full h-[52px] font-bold rounded-[14px] border-none",
                    )
                    btn_final_download = gr.DownloadButton(
                        "📥 下載合併後的檔案",
                        visible=False,
                        elem_id="btn-download",
                        elem_classes="w-full h-[52px] font-bold rounded-[14px] border-none mt-3",
                    )
                    error_msg_results = gr.HTML("", visible=False)
            
                    btn_process_another = gr.Button(
                        "處理新檔案",
                        elem_id="btn-reset",
                        elem_classes="w-full h-[44px] font-bold rounded-[10px] border-none mt-3",
                    )
    
    # -- Event Wiring --------------------------------------------------

    detect_btn.click(
        fn=detect_chapters,
        inputs=[file_upload],
        outputs=[screen_start, screen_results, chapter_checkboxes, error_msg_start, stats_html],
        api_name=False,
        show_progress="full"
    )

    btn_select_all.click(
        fn=select_all, 
        inputs=[], 
        outputs=[chapter_checkboxes], 
        api_name=False
    )
    
    btn_clear_all.click(
        fn=clear_all, 
        inputs=[], 
        outputs=[chapter_checkboxes], 
        api_name=False
    )

    chapter_checkboxes.change(
        fn=update_selection_count,
        inputs=[chapter_checkboxes],
        outputs=[status_selected],
        api_name=False
    )

    btn_merge.click(
        fn=download_chapters,
        inputs=[chapter_checkboxes, page_shift_slider],
        outputs=[btn_final_download, error_msg_results],
        api_name=False,
        show_progress="full"
    )
    
    btn_process_another.click(
        fn=reset_to_start,
        inputs=[],
        outputs=[screen_start, screen_results, file_upload],
        api_name=False
    )


if __name__ == "__main__":
    out_dir = os.path.abspath("outputs")
    os.makedirs(out_dir, exist_ok=True)
    
    # 啟用佇列系統以支援進度條
    demo.queue(
        max_size=20,
        default_concurrency_limit=5
    ).launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        allowed_paths=[out_dir],
        show_api=False,
    )
