import streamlit as st
import os
from io import BytesIO
import zipfile
from PIL import Image, ImageOps, ImageFilter
import base64

# PDF Libraries
from PyPDF2 import PdfReader, PdfWriter

# PPT Libraries
from pptx import Presentation

# Jupyter Notebook Libraries
import nbformat
from nbconvert import HTMLExporter
from xhtml2pdf import pisa

# PDF to Image
try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False
except Exception:
    HAS_PDF2IMAGE = False

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DocMint - Pro Workspace",
    page_icon="🍃",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE ---
if 'current_tool' not in st.session_state:
    st.session_state['current_tool'] = "Compress Docs"

# Path to local logo (fallback to remote if not found)
LOCAL_LOGO_PATH = "/mnt/data/ee0a0a38-adb8-4836-9e16-1632d846a6d9.png"
REMOTE_LOGO_URL = "https://github.com/nitesh4004/Ni30-pdflover/blob/main/docmint.png?raw=true"

# --- 3. CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root{
        --bg: #f8fafc;
        --panel: #ffffff;
        --muted: #94a3b8;
        --text: #0f172a;
        --accent: #0ea5a4;
        --primary: #0b69ff;
        --border: #e6eef6;
        --result-bg: #f1f9ff;
        --nav-hover: #e6f6f9;
    }

    html, body, [class*="css"] {
        background-color: var(--bg);
        font-family: 'Inter', sans-serif;
        color: var(--text);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15,23,42,0.02) 0%, rgba(14,165,164,0.03) 100%);
        border-right: 1px solid var(--border);
        padding: 1rem;
    }

    /* Centered Logo Area */
    .sidebar-logo-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 0.8rem 0;
        margin-bottom: 0.9rem;
        border-bottom: 1px solid var(--border);
    }
    .sidebar-logo-img {
        width: 110px;
        height: 110px;
        object-fit: cover;
        border-radius: 12px;
        box-shadow: 0 6px 18px rgba(15,23,42,0.06);
        border: 1px solid rgba(11,105,255,0.06);
    }
    .sidebar-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: var(--text);
        letter-spacing: -0.2px;
        margin-top: 4px;
        margin-bottom: 0px;
    }
    .sidebar-sub {
        font-size: 0.86rem;
        color: var(--muted);
        margin-top: 0px;
    }

    /* Sidebar section captions */
    .stCaption {
        color: var(--accent) !important;
        font-weight: 700;
        margin-top: 0.6rem;
        margin-bottom: 0.2rem;
    }

    /* Nav Buttons */
    div.stButton > button {
        width: 100%;
        display:flex;
        align-items:center;
        gap:10px;
        justify-content:flex-start;
        border-radius: 10px;
        border: 1px solid transparent;
        background-color: transparent;
        color: #334155;
        text-align: left;
        padding: 0.6rem 0.9rem;
        transition: all 0.14s ease-in-out;
        font-weight:600;
    }
    div.stButton > button:hover {
        background-color: var(--nav-hover);
        color: var(--text);
        transform: translateY(-1px);
    }

    /* Primary Action Buttons */
    div.stButton > button[kind="primary"] {
        background-color: var(--primary);
        color: white;
        border: none;
        box-shadow: 0 6px 16px rgba(11,105,255,0.12);
    }

    /* Result Area Box */
    .result-box {
        background-color: var(--result-bg);
        border: 1px solid rgba(11,105,255,0.08);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin-top: 1.6rem;
        box-shadow: 0 8px 24px rgba(12, 74, 175, 0.02);
    }

    .stFileUploader {
        border-radius: 10px;
        border: 1px dashed var(--border);
        padding: 0.6rem;
        background: var(--panel);
    }

    @media (max-width: 768px) {
        .sidebar-logo-img { width: 88px; height: 88px; }
        .sidebar-title { font-size:1.1rem; }
    }
</style>
""", unsafe_allow_html=True)

# --- 4. HELPER FUNCTIONS ---
def create_zip(files_dict, zip_name):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file_name, data in files_dict.items():
            zip_file.writestr(file_name, data)
    return zip_buffer.getvalue()

def get_size_format(b, factor=1024, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P"]:
        if b < factor: return f"{b:.2f} {unit}{suffix}"
        b /= factor
    return f"{b:.2f} Y{suffix}"

def compress_image_to_target(img, target_kb):
    target_bytes = target_kb * 1024
    low, high = 1, 95
    best_buffer = None
    
    # 1. Optimize Quality
    while low <= high:
        mid = (low + high) // 2
        buf = BytesIO()
        if img.mode in ("RGBA", "P"): temp_img = img.convert("RGB")
        else: temp_img = img
        temp_img.save(buf, format="JPEG", quality=mid, optimize=True)
        size = buf.tell()
        
        if size <= target_bytes:
            best_buffer = buf
            low = mid + 1 
        else:
            high = mid - 1
            
    if best_buffer: return best_buffer, "Quality Optimized"
        
    # 2. Resize if needed
    scale = 0.9
    width, height = img.size
    while scale > 0.1:
        new_w, new_h = int(width * scale), int(height * scale)
        buf = BytesIO()
        if img.mode in ("RGBA", "P"): temp_img = img.convert("RGB")
        else: temp_img = img
        resized = temp_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        resized.save(buf, format="JPEG", quality=50, optimize=True)
        if buf.tell() <= target_bytes: return buf, f"Resized to {int(scale*100)}%"
        scale -= 0.1
    return None, "Failed"

def convert_notebook_to_pdf_bytes(notebook_file, font_family="Helvetica"):
    """
    Converts uploaded .ipynb file to PDF bytes using nbconvert -> HTML -> xhtml2pdf.
    """
    try:
        # 1. Read Notebook
        notebook_content = notebook_file.read().decode('utf-8')
        notebook = nbformat.reads(notebook_content, as_version=4)

        # 2. Convert to HTML
        html_exporter = HTMLExporter()
        html_exporter.template_name = 'classic'
        (body, resources) = html_exporter.from_notebook_node(notebook)

        # 3. Add Custom CSS for Font
        # xhtml2pdf supports limited CSS. We inject the font preference.
        css_style = f"""
        <style>
            @page {{
                size: a4 portrait;
                margin: 2cm;
            }}
            body {{
                font-family: {font_family}, sans-serif;
                font-size: 10pt;
            }}
            div.cell {{
                width: 100%;
                margin-bottom: 10px;
            }}
        </style>
        """
        full_html = f"<html><head>{css_style}</head><body>{body}</body></html>"

        # 4. Convert HTML to PDF
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(
            src=full_html,
            dest=pdf_buffer
        )

        if pisa_status.err:
            return None, "Error in PDF generation"
        
        return pdf_buffer.getvalue(), "Success"

    except Exception as e:
        return None, str(e)

# --- 5. SIDEBAR ---
def render_sidebar():
    with st.sidebar:
        # Use local logo if available; otherwise use remote URL
        logo_to_show = LOCAL_LOGO_PATH if os.path.exists(LOCAL_LOGO_PATH) else REMOTE_LOGO_URL

        # Markup wrapper
        if os.path.exists(LOCAL_LOGO_PATH):
            st.markdown('<div class="sidebar-logo-wrap">', unsafe_allow_html=True)
            st.image(LOCAL_LOGO_PATH, use_column_width=False, width=110)
            st.markdown(f"<div style='text-align:center;'><div class='sidebar-title'>DocMint</div><div class='sidebar-sub'>Web App — Pro Workspace</div></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="sidebar-logo-wrap">
                <img src="{REMOTE_LOGO_URL}" class="sidebar-logo-img" />
                <div style='text-align:center;'>
                    <div class="sidebar-title">DocMint</div>
                    <div class="sidebar-sub">Web App — Pro Workspace</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.caption("NEW TOOLS")
        if st.button("Compress Docs"): st.session_state['current_tool'] = "Compress Docs"

        st.caption("CONVERTERS")
        if st.button("Notebook to PDF"): st.session_state['current_tool'] = "Notebook to PDF"
        if st.button("Convert Format"): st.session_state['current_tool'] = "Convert Format"
        if st.button("JPG to PDF"): st.session_state['current_tool'] = "JPG to PDF"

        st.caption("IMAGE TOOLS")
        if st.button("Resize Image"): st.session_state['current_tool'] = "Resize Image"
        if st.button("Image Editor"): st.session_state['current_tool'] = "Image Editor"
        
        st.caption("PDF TOOLS")
        if st.button("Merge PDF"): st.session_state['current_tool'] = "Merge PDF"
        if st.button("Split PDF"): st.session_state['current_tool'] = "Split PDF"
        
        st.write("")
        st.caption("OFFICE TOOLS")
        if st.button("Merge PPTX"): st.session_state['current_tool'] = "Merge PPTX"

# --- 6. TOOLS ---
def tool_compress_docs():
    st.markdown("### Compress Documents")
    
    doc_type = st.radio("Select Type", ["Image (Target Size)", "PDF (Reduce Size)"], horizontal=True)
    st.markdown("---")
    
    if doc_type == "Image (Target Size)":
        uploaded = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
        if uploaded:
            img = Image.open(uploaded)
            current_kb = uploaded.size / 1024
            
            c1, c2 = st.columns(2)
            c1.metric("Current Size", f"{current_kb:.1f} KB")
            
            target_kb = c2.number_input("Target Size (KB)", min_value=10, max_value=int(current_kb), value=int(current_kb*0.8))
            
            if st.button("Compress Now", type="primary", use_container_width=True):
                with st.spinner("Compressing..."):
                    res_buf, method = compress_image_to_target(img, target_kb)
                    if res_buf:
                        st.markdown('<div class="result-box">', unsafe_allow_html=True)
                        st.success(f"✅ Success! ({method})")
                        st.download_button("Download Result", res_buf.getvalue(), f"compressed_{uploaded.name}", "image/jpeg", type="primary")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.error("Could not reach target size.")
                        
    else: # PDF
        uploaded = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded:
            st.metric("Current Size", get_size_format(uploaded.size))
            level = st.select_slider("Compression Strength", options=["Low", "Medium", "High"], value="Medium")
            
            if st.button("Compress PDF", type="primary", use_container_width=True):
                with st.spinner("Compressing..."):
                    reader = PdfReader(uploaded)
                    writer = PdfWriter()
                    for page in reader.pages:
                        if level in ["Medium", "High"]: page.compress_content_streams()
                        writer.add_page(page)
                    if level == "High": writer.add_metadata({})
                    
                    out = BytesIO()
                    writer.write(out)
                    
                    st.markdown('<div class="result-box">', unsafe_allow_html=True)
                    st.success(f"Done! New Size: {get_size_format(out.tell())}")
                    st.download_button("Download PDF", out.getvalue(), f"compressed_{uploaded.name}", "application/pdf", type="primary")
                    st.markdown('</div>', unsafe_allow_html=True)

def tool_resize_image():
    st.markdown("### Resize Image")
    uploaded = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp"])
    
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption=f"Original: {img.width}x{img.height}", width=300)
        st.markdown("---")
        
        # Settings Row
        c1, c2, c3 = st.columns(3)
        unit = c1.selectbox("Unit", ["Pixels", "Percent"])
        fmt = c2.selectbox("Format", ["JPG", "PNG", "WEBP"])
        lock = c3.checkbox("Lock Ratio", value=True)
        
        c4, c5 = st.columns(2)
        if unit == "Pixels":
            w = c4.number_input("Width", value=img.width)
            if lock:
                h = int(w * (img.height/img.width))
                c5.number_input("Height (Auto)", value=h, disabled=True)
            else:
                h = c5.number_input("Height", value=img.height)
        else:
            pct = st.slider("Percentage", 1, 200, 100)
            w, h = int(img.width * (pct/100)), int(img.height * (pct/100))
            st.caption(f"Output: {w} x {h}")

        if st.button("Resize Image", type="primary", use_container_width=True):
            new_img = img.resize((w, h), Image.Resampling.LANCZOS)
            b = BytesIO()
            save_fmt = "JPEG" if fmt == "JPG" else fmt
            if save_fmt == "JPEG" and new_img.mode in ("RGBA", "P"): new_img = new_img.convert("RGB")
            new_img.save(b, format=save_fmt, quality=95)
            
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.image(new_img, caption="Resized Result", width=300)
            st.download_button("Download Image", b.getvalue(), f"resized.{save_fmt.lower()}", f"image/{save_fmt.lower()}", type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

def tool_img_editor():
    st.markdown("### Image Editor")
    uploaded = st.file_uploader("Upload Image", type=["png", "jpg"])
    
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="Original", width=300)
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        angle = c1.slider("Rotate", 0, 360, 0)
        filt = c2.selectbox("Filter", ["None", "Grayscale", "Blur", "Sharpen", "Contour"])
        
        if st.button("Apply Changes", type="primary", use_container_width=True):
            processed = img.copy()
            if angle: processed = processed.rotate(angle, expand=True)
            if filt == "Grayscale": processed = ImageOps.grayscale(processed)
            elif filt == "Blur": processed = processed.filter(ImageFilter.BLUR)
            elif filt == "Sharpen": processed = processed.filter(ImageFilter.SHARPEN)
            elif filt == "Contour": processed = processed.filter(ImageFilter.CONTOUR)
            
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.image(processed, caption="Edited Result", width=300)
            b = BytesIO()
            fmt = img.format if img.format else "PNG"
            processed.save(b, format=fmt)
            st.download_button("Download Image", b.getvalue(), f"edited.{fmt.lower()}", f"image/{fmt.lower()}", type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

def tool_merge_pdf():
    st.markdown("### Merge PDFs")
    files = st.file_uploader("Select PDF Files", type="pdf", accept_multiple_files=True)
    
    if files:
        file_map = {f.name: f for f in files}
        st.write("Drag to reorder:")
        order = st.multiselect("Sequence", list(file_map.keys()), default=list(file_map.keys()))
        
        if st.button("Merge Files", type="primary", use_container_width=True):
            merger = PdfWriter()
            for name in order: merger.append(file_map[name])
            out = BytesIO()
            merger.write(out)
            
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.success("PDFs Merged Successfully!")
            st.download_button("Download Merged PDF", out.getvalue(), "merged.pdf", "application/pdf", type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

def tool_split_pdf():
    st.markdown("### Split PDF")
    f = st.file_uploader("Upload PDF", type="pdf")
    
    if f:
        reader = PdfReader(f)
        total = len(reader.pages)
        st.info(f"Detected {total} Pages")
        
        mode = st.radio("Action", ["Extract Single Page", "Split All to ZIP"], horizontal=True)
        
        if mode == "Extract Single Page":
            p_num = st.number_input("Page Number", 1, total, 1)
            if st.button("Extract Page", type="primary", use_container_width=True):
                w = PdfWriter()
                w.add_page(reader.pages[p_num-1])
                o = BytesIO()
                w.write(o)
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.download_button("Download Page", o.getvalue(), f"page_{p_num}.pdf", "application/pdf", type="primary")
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            if st.button("Split All Pages", type="primary", use_container_width=True):
                files = {}
                for i in range(total):
                    w = PdfWriter()
                    w.add_page(reader.pages[i])
                    o = BytesIO()
                    w.write(o)
                    files[f"page_{i+1}.pdf"] = o.getvalue()
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.success("All pages split successfully!")
                st.download_button("Download ZIP", create_zip(files, "split.zip"), "split.zip", "application/zip", type="primary")
                st.markdown('</div>', unsafe_allow_html=True)

def tool_convert_format():
    st.markdown("### Convert Format")
    u = st.file_uploader("Upload Image", type=["png", "jpg", "webp"])
    
    if u:
        st.image(u, width=200)
        target = st.selectbox("Convert To", ["PNG", "JPEG", "PDF", "WEBP"])
        
        if st.button("Convert File", type="primary", use_container_width=True):
            i = Image.open(u)
            if target == "JPEG" and i.mode == "RGBA": i = i.convert("RGB")
            b = BytesIO()
            i.save(b, format=target)
            mime = "application/pdf" if target == "PDF" else f"image/{target.lower()}"
            
            st.markdown('<div class="result-box">', unsafe_allow_html=True)
            st.download_button(f"Download {target}", b.getvalue(), f"converted.{target.lower()}", mime, type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

def tool_notebook_to_pdf():
    st.markdown("### Jupyter Notebook to PDF")
    
    # Font Selection as requested
    st.caption("Customization")
    font_choice = st.selectbox("Select Font Style", ["Helvetica (Sans-Serif)", "Times New Roman (Serif)"])
    
    font_map = {
        "Helvetica (Sans-Serif)": "Helvetica",
        "Times New Roman (Serif)": "Times New Roman"
    }
    selected_font = font_map[font_choice]

    uploaded = st.file_uploader("Upload .ipynb file", type=["ipynb"])
    
    if uploaded:
        st.write("File loaded. Ready to convert.")
        
        if st.button("Convert to PDF", type="primary", use_container_width=True):
            with st.spinner("Converting Notebook... this may take a moment"):
                # Reset file pointer if re-running
                uploaded.seek(0)
                pdf_bytes, status = convert_notebook_to_pdf_bytes(uploaded, selected_font)
                
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                if pdf_bytes:
                    st.success(f"Conversion Successful using {selected_font}!")
                    st.download_button("Download PDF", pdf_bytes, f"{uploaded.name}.pdf", "application/pdf", type="primary")
                else:
                    st.error(f"Conversion Failed: {status}")
                st.markdown('</div>', unsafe_allow_html=True)

# --- 7. MAIN ROUTING ---
render_sidebar()
tool = st.session_state['current_tool']

if tool == "Compress Docs": tool_compress_docs()
elif tool == "Resize Image": tool_resize_image()
elif tool == "Image Editor": tool_img_editor()
elif tool == "Merge PDF": tool_merge_pdf()
elif tool == "Split PDF": tool_split_pdf()
elif tool == "Convert Format": tool_convert_format()
elif tool == "Notebook to PDF": tool_notebook_to_pdf()
elif tool == "JPG to PDF":
    st.markdown("### JPG to PDF")
    u = st.file_uploader("Upload Images", type=["png", "jpg"], accept_multiple_files=True)
    if u and st.button("Create PDF", type="primary", use_container_width=True):
        imgs = [Image.open(f).convert("RGB") for f in u]
        b = BytesIO()
        imgs[0].save(b, "PDF", save_all=True, append_images=imgs[1:])
        st.markdown('<div class="result-box">', unsafe_allow_html=True)
        st.download_button("Download PDF", b.getvalue(), "docmint_images.pdf", "application/pdf", type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
elif tool == "Merge PPTX":
     st.markdown("### Merge PPTX")
     st.info("Coming soon in next update!")
else:
    st.info("Select a tool from the sidebar.")

st.markdown("---")
st.markdown("<div style='text-align:center; color:#64748b; font-size:0.82rem;'>© 2024 DocMint by Nitesh Kumar</div>", unsafe_allow_html=True)
