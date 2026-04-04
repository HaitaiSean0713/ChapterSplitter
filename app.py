"""
Chapter Splitter Tool — Gradio App
設計系統：The Precision Curator (依 DESIGN.md & 使用者指定 Tailwind UI)
"""
import os
import tempfile
import gradio as gr
import re

from splitter.pdf_splitter import detect_chapters_pdf
from splitter.docx_splitter import detect_chapters_docx
from splitter.txt_splitter import detect_chapters_txt
from splitter.merger import merge_selected

# ── Global state ────────────────────────────────────────────────
_chapters: list[dict] = []
_file_path: str = ""
_file_type: str = ""

EXT_MAP = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".txt": "txt",
}

# ── Design Tokens & Tailwind Config ──────────────────────────────
HEAD = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script>
function _applyTailwindConfig() {
    tailwind.config = {
        darkMode: "class",
        theme: {
            extend: {
                colors: {
                    "primary-container": "#0071e3",
                    "inverse-primary": "#abc7ff",
                    "on-secondary-container": "#3e5682",
                    "tertiary-fixed-dim": "#ffb693",
                    "error": "#ba1a1a",
                    "tertiary-container": "#c25100",
                    "on-surface": "#1b1b1d",
                    "outline": "#717785",
                    "surface-container-highest": "#e4e2e4",
                    "on-tertiary-fixed-variant": "#7a3000",
                    "surface-tint": "#005cbb",
                    "surface-container-high": "#eae7ea",
                    "outline-variant": "#c1c6d6",
                    "error-container": "#ffdad6",
                    "secondary-container": "#b4ccff",
                    "on-background": "#1b1b1d",
                    "primary": "#0059b5",
                    "primary-fixed": "#d7e2ff",
                    "surface-container-lowest": "#ffffff",
                    "on-secondary": "#ffffff",
                    "surface-container-low": "#f6f3f5",
                    "on-primary": "#ffffff",
                    "on-primary-container": "#fcfbff",
                    "inverse-surface": "#303032",
                    "surface-bright": "#fcf8fb",
                    "on-tertiary": "#ffffff",
                    "on-error-container": "#93000a",
                    "secondary-fixed": "#d7e2ff",
                    "on-primary-fixed": "#001b3f",
                    "surface": "#fcf8fb",
                    "on-error": "#ffffff",
                    "on-tertiary-fixed": "#341000",
                    "surface-dim": "#dcd9dc",
                    "secondary": "#465e8b",
                    "secondary-fixed-dim": "#aec7f9",
                    "background": "#fcf8fb",
                    "on-primary-fixed-variant": "#00458f",
                    "on-secondary-fixed-variant": "#2e4772",
                    "inverse-on-surface": "#f3f0f2",
                    "primary-fixed-dim": "#abc7ff",
                    "tertiary-fixed": "#ffdbcb",
                    "on-tertiary-container": "#fffaf9",
                    "on-surface-variant": "#414753",
                    "on-secondary-fixed": "#001b3f",
                    "surface-variant": "#e4e2e4",
                    "surface-container": "#f0edef",
                    "tertiary": "#9b3f00"
                },
                fontFamily: {
                    headline: ["Inter", "sans-serif"],
                    body: ["Inter", "sans-serif"]
                }
            }
        }
    };
}
</script>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries" onload="_applyTailwindConfig()"></script>
"""

CSS = """
body, .gradio-container {
    background-color: #fcf8fb !important;
    font-family: 'Inter', sans-serif !important;
    color: #1b1b1d !important;
}
.material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
}
.apple-shadow {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08) !important;
}
.glass-header {
    background-color: rgba(255, 255, 255, 0.8) !important;
    backdrop-filter: blur(20px) !important;
}
.gradio-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* Hide default gradio padding/borders around main container */
#main-app { padding: 0 !important; }

/* Custom grad style for checkboxes */
#chapter-list {
    background: transparent !important;
    border: none !important;
    gap: 8px !important;
    display: flex !important;
    flex-direction: column !important;
}
#chapter-list label {
    background: #ffffff !important;
    border-radius: 8px !important;
    padding: 20px !important;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04) !important;
    transition: all 0.2s !important;
    display: flex !important;
    align-items: center !important;
    border: none !important;
    width: 100% !important;
    cursor: pointer !important;
}
#chapter-list label:hover {
    transform: scale(1.01) !important;
}
#chapter-list label:has(input:checked) {
    background: #F0F7FF !important;
    border-left: 3px solid #0071e3 !important;
}
#chapter-list input[type="checkbox"] {
    appearance: none;
    -webkit-appearance: none;
    width: 22px !important;
    height: 22px !important;
    border-radius: 50% !important;
    border: 1.5px solid #d1d1d6 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-right: 16px !important;
    transition: all 0.2s ease !important;
    flex-shrink: 0 !important;
}
#chapter-list input[type="checkbox"]:checked {
    background-color: #0071e3 !important;
    border-color: #0071e3 !important;
}
#chapter-list input[type="checkbox"]:checked::after {
    content: 'check' !important;
    font-family: 'Material Symbols Outlined' !important;
    font-size: 14px !important;
    color: white !important;
    font-weight: bold !important;
}
#chapter-list span {
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #1b1b1d !important;
}

/* Base resets for Gradio inner elements */
#upload-zone .upload-container {
    border: none !important;
    background: transparent !important;
}
#status-selected span {
    font-size: 13px !important;
    color: #465e8b !important;
}
"""

def _get_ext(path: str) -> str:
    _, ext = os.path.splitext(path)
    return ext.lower()

def detect_chapters(file_obj):
    global _chapters, _file_path, _file_type
    
    if file_obj is None:
        return (
            gr.update(visible=True),   # start screen
            gr.update(visible=False),  # results screen
            gr.update(choices=[], value=[]),                        # checkboxes
            gr.update(value='<p class="text-error text-center mt-2 text-sm font-bold">❌ 請加上檔案</p>', visible=True), # error text
            gr.update(value="")                         # stats html
        )
        
    path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    ext = _get_ext(path)
    file_type = EXT_MAP.get(ext)

    if file_type is None:
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(choices=[], value=[]),
            gr.update(value=f'<p class="text-error text-center mt-2 text-sm font-bold">❌ 不支援的格式「{ext}」</p>', visible=True),
            gr.update(value="")
        )
        
    try:
        if file_type == "pdf":
            chapters = detect_chapters_pdf(path)
        elif file_type == "docx":
            chapters = detect_chapters_docx(path)
        else:
            chapters = detect_chapters_txt(path)

        _chapters = chapters
        _file_path = path
        _file_type = file_type

        labeled = [f"{i+1}. {c['title']}" for i, c in enumerate(chapters)]
        
        # Build Stats HTML
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        stats_html = f'''
        <div class="bg-surface-container-lowest rounded-lg apple-shadow p-6 flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="text-[17px] font-bold">📄 偵測完成</span>
                </div>
                <span class="px-4 py-1.5 rounded-full text-white text-[13px] font-bold" style="background-color: #0059b5; color: white !important;">共 {len(labeled)} 個章節</span>
            </div>
            <div class="flex flex-wrap gap-2">
                <div class="bg-surface-container-low px-3 py-1.5 rounded-[8px] flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-[16px] text-secondary" data-icon="description">description</span>
                    <span class="text-[12px] text-secondary font-medium">偵測方式：自動擷取</span>
                </div>
                <div class="bg-surface-container-low px-3 py-1.5 rounded-[8px] flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-[16px] text-secondary" data-icon="database">database</span>
                    <span class="text-[12px] text-secondary font-medium">檔案大小：{file_size_mb:.1f} MB</span>
                </div>
            </div>
        </div>
        '''

        return (
            gr.update(visible=False), # hide start screen
            gr.update(visible=True),  # show results screen
            gr.update(choices=labeled, value=labeled), # checkboxes selected by default
            gr.update(value="", visible=False),
            gr.update(value=stats_html)
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(choices=[], value=[]),
            gr.update(value=f'<p class="text-error text-center mt-2 text-sm font-bold">❌ 發生錯誤：{e}</p>', visible=True),
            gr.update(value="")
        )

def select_all():
    global _chapters
    labeled = [f"{i+1}. {c['title']}" for i, c in enumerate(_chapters)]
    return gr.update(value=labeled)

def clear_all():
    return gr.update(value=[])

def update_selection_count(selected):
    global _chapters
    return f'<span class="text-secondary text-[13px] font-bold ml-auto pr-2">已選 {len(selected)} / {len(_chapters)} 章節</span>'

def download_chapters(selected_labels: list[str], page_shift: float):
    global _chapters, _file_path, _file_type
    print(f"[DEBUG] download_chapters called with {len(selected_labels)} labels, page_shift={page_shift}")

    if not selected_labels:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value='<p class="text-error text-center mt-2 text-sm font-bold">❌ 請至少勾選一個章節。</p>', visible=True)

    try:
        selected_titles = []
        for label in selected_labels:
            dot_pos = label.index(". ")
            idx = int(label[:dot_pos]) - 1
            selected_titles.append(_chapters[idx]["title"])

        print(f"[DEBUG] merging: {selected_titles}")
        data, mime = merge_selected(_file_path, _file_type, _chapters, selected_titles, int(page_shift))
        print(f"[DEBUG] merge done, data size={len(data)}, mime={mime}")

        ext_map = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain; charset=utf-8": ".txt",
        }
        suffix = ext_map.get(mime, ".bin")

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
        print(f"[DEBUG] file saved to: {out_path}")
        print(f"[DEBUG] Merge successful.")

        return (
            gr.update(value=out_path, visible=True), # btn_final_download
            gr.update(value='<p class="text-[#34C759] text-center mt-2 text-sm font-bold">✅ 合併完成！檔案已準備就緒，請點擊下方下載按鈕。</p>', visible=True) # show success text
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            gr.update(visible=False), 
            gr.update(value=f'<p class="text-error text-center mt-2 text-sm font-bold">❌ 錯誤：{str(e)}</p>', visible=True)
        )

def reset_to_start():
    global _chapters, _file_path, _file_type
    _chapters = []
    _file_path = ""
    _file_type = ""
    return (
        gr.update(visible=True),   # start screen
        gr.update(visible=False),  # results screen
        gr.update(value=None)      # reset file upload
    )

def reset_to_results():
    return (
        gr.update(visible=False),  # start screen
        gr.update(visible=True),   # results screen
        gr.update(visible=False)   # success screen
    )


# ── UI Construction ──────────────────────────────────────────────

with gr.Blocks(css=CSS, head=HEAD, theme=gr.themes.Base()) as demo:
    
    # === SCREEN 1: Start / Tool Screen ===
    with gr.Column(elem_id="screen-start") as screen_start:
        
        # Header
        gr.HTML('''
        <header class="w-full glass-nav flex flex-col items-center justify-center py-4 px-6 border-b border-outline-variant/15">
            <div class="flex flex-col items-center text-center">
                <h1 class="text-[20px] font-bold text-[#1b1b1d] tracking-tight">章節拆分工具</h1>
                <p class="text-sm font-light text-[#414753] mt-0.5">支援 PDF・Word・Markdown</p>
            </div>
        </header>
        ''')
        
        with gr.Column(elem_classes="max-w-[640px] mx-auto pt-8 pb-24 px-6 min-h-screen flex flex-col gap-8 w-full"):
            
            # Warning Card
            gr.HTML('''
            <section class="bg-[#FFF9E6] p-6 rounded-[16px] flex flex-col gap-4">
                <div class="flex items-center gap-2 text-[#9B3F00]">
                    <span class="material-symbols-outlined" data-icon="warning" style="font-variation-settings: 'FILL' 1;">warning</span>
                    <h2 class="font-bold">使用提醒</h2>
                </div>
                <div class="grid grid-cols-1 gap-y-3">
                    <div class="flex items-start gap-3 text-sm text-[#414753]">
                        <span class="material-symbols-outlined text-green-600 text-[18px]" data-icon="check_circle" style="font-variation-settings: 'FILL' 1;">check_circle</span>
                        <span>大學課本 PDF（含目錄書籤）</span>
                    </div>
                    <div class="flex items-start gap-3 text-sm text-[#414753]">
                        <span class="material-symbols-outlined text-green-600 text-[18px]" data-icon="check_circle" style="font-variation-settings: 'FILL' 1;">check_circle</span>
                        <span>有標題樣式的 Word 文件（.docx）</span>
                    </div>
                    <div class="flex items-start gap-3 text-sm text-[#414753]">
                        <span class="material-symbols-outlined text-green-600 text-[18px]" data-icon="check_circle" style="font-variation-settings: 'FILL' 1;">check_circle</span>
                        <span>Markdown 文件（.md）</span>
                    </div>
                    <div class="flex items-start gap-3 text-sm text-[#414753]">
                        <span class="material-symbols-outlined text-red-600 text-[18px]" data-icon="cancel" style="font-variation-settings: 'FILL' 1;">cancel</span>
                        <span>掃描版圖片 PDF</span>
                    </div>
                    <div class="flex items-start gap-3 text-sm text-[#414753]">
                        <span class="material-symbols-outlined text-red-600 text-[18px]" data-icon="cancel" style="font-variation-settings: 'FILL' 1;">cancel</span>
                        <span>無章節結構的純文字</span>
                    </div>
                </div>
            </section>
            ''')
            
            # Upload Card
            with gr.Column(elem_id="upload-zone", elem_classes="bg-white p-4 rounded-[16px] shadow-[0_2px_12px_rgba(27,27,29,0.08)]"):
                file_upload = gr.File(label="拖曳檔案至此 或點擊上傳", file_types=[".pdf", ".docx", ".doc", ".txt"], type="filepath")
                detect_btn = gr.Button("🔍 開始偵測章節", elem_classes="w-full mt-4 h-[52px] bg-[#0059b5] text-white font-bold rounded-[14px] shadow-lg flex items-center justify-center gap-2 hover:bg-[#004fa0] border-none")
                error_msg_start = gr.HTML("", visible=False)




    # === SCREEN 2: Results Screen ===
    with gr.Column(elem_id="screen-results", visible=False) as screen_results:
        
        # Header Nav
        gr.HTML('''
        <header class="fixed top-0 w-full z-50 glass-header border-b border-zinc-200 shadow-sm bg-white/80">
            <div class="flex items-center px-4 h-16 w-full max-w-7xl mx-auto justify-between">
                <div class="flex items-center gap-2">
                    <h1 class="font-headline font-bold text-[20px] tracking-tight text-on-surface ml-2">章節拆分工具</h1>
                </div>
            </div>
        </header>
        ''')
        
        with gr.Column(elem_classes="pt-24 pb-48 px-4 max-w-2xl mx-auto w-full"):
            
            stats_html = gr.HTML("")
            
            with gr.Row(elem_classes="mb-4 flex flex-row items-center justify-start px-2 mt-4"):
                btn_select_all = gr.Button("全選", elem_classes="text-[#0059b5] bg-transparent shadow-none border-none hover:opacity-70 font-bold text-[15px]", scale=0, min_width=80)
                btn_clear_all = gr.Button("全取消", elem_classes="text-[#0059b5] bg-transparent shadow-none border-none hover:opacity-70 font-bold text-[15px]", scale=0, min_width=80)
                status_selected = gr.HTML('<span class="text-secondary text-[13px] font-bold ml-auto pr-2">已選 0 章節</span>', elem_id="status-selected")
                
            chapter_checkboxes = gr.CheckboxGroup(label="", choices=[], elem_id="chapter-list", container=False)
            
            # Form padding
            gr.HTML('<div class="h-10"></div>')
            
            # Bottom Fixed Action Bar
            with gr.Column(elem_classes="fixed bottom-0 left-0 w-full bg-white border-t border-zinc-200 shadow-[0_-4px_20px_rgba(0,0,0,0.03)] z-50 pb-6 pt-4 px-6"):
                page_shift_slider = gr.Slider(
                    minimum=-2, maximum=2, step=1, value=-1, 
                    label="封面頁校正 (如果這章的封面出現在上一章，請改為 0 或 -2)",
                    elem_classes="mb-3 max-w-2xl mx-auto"
                )
                btn_merge = gr.Button("🔨 開始合併已選章節", elem_classes="w-full max-w-2xl mx-auto h-[52px] bg-[#0059b5] text-white font-bold rounded-[14px] shadow-lg flex items-center justify-center hover:bg-[#004fa0] border-none")
                btn_final_download = gr.DownloadButton("📥 下載合併後的檔案", visible=False, elem_classes="w-full max-w-2xl mx-auto h-[52px] bg-[#34C759] text-white font-bold rounded-[14px] shadow-lg flex items-center justify-center hover:bg-[#28a745] border-none mt-3")
                error_msg_results = gr.HTML("", visible=False)
                
                with gr.Row(elem_classes="max-w-2xl mx-auto mt-3 gap-3 w-full"):
                    btn_process_another = gr.Button("處理新檔案", elem_classes="flex-1 h-[44px] bg-zinc-100 text-[#1b1b1d] font-bold rounded-[10px] hover:bg-zinc-200 border-none")

    # ── Event Wiring ─────────────────────────────────────────────

    detect_btn.click(
        fn=detect_chapters,
        inputs=[file_upload],
        outputs=[screen_start, screen_results, chapter_checkboxes, error_msg_start, stats_html]
    )

    btn_select_all.click(fn=select_all, inputs=[], outputs=[chapter_checkboxes])
    btn_clear_all.click(fn=clear_all, inputs=[], outputs=[chapter_checkboxes])
    
    chapter_checkboxes.change(
        fn=update_selection_count,
        inputs=[chapter_checkboxes],
        outputs=[status_selected]
    )

    btn_merge.click(
        fn=download_chapters,
        inputs=[chapter_checkboxes, page_shift_slider],
        outputs=[btn_final_download, error_msg_results]
    )

    btn_process_another.click(
        fn=reset_to_start,
        inputs=[],
        outputs=[screen_start, screen_results, file_upload]
    )


if __name__ == "__main__":
    out_dir = os.path.abspath("outputs")
    os.makedirs(out_dir, exist_ok=True)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        inbrowser=True,
        allowed_paths=[out_dir],
    )
