import streamlit as st
import os
from io import BytesIO
import zipfile
from PIL import Image, ImageOps, ImageFilter

# PDF Libraries
from PyPDF2 import PdfReader, PdfWriter

# PPT Libraries
from pptx import Presentation

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
    layout="centered", # Changed to centered for better vertical flow focus
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE ---
if 'current_tool' not in st.session_state:
    st.session_state['current_tool'] = "Compress Docs"

# --- 3. CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1e293b;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

    /* Logo Area */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 1rem 0;
        margin-bottom: 1rem;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f172a;
    }

    /* Nav Buttons */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid transparent;
        background-color: transparent;
        color: #475569;
        text-align: left;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    
    div.stButton > button:hover {
        background-color: #e2e8f0;
        color: #0f172a;
    }

    /* Primary Action Buttons */
    div.stButton > button[kind="primary"] {
        background-color: #007AFF;
        color: white;
        border: none;
    }

    /* Result Area Box */
    .result-box {
        background-color: #f1f5f9;
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin-top: 2rem;
    }
    
    h3 { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; text-align: center; }
    h4 { font-size: 1rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; color: #334155; }

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

# --- 5. SIDEBAR ---
def render_sidebar():
    with st.sidebar:
        logo_url = "https://github.com/nitesh4004/Ni30-pdflover/blob/main/docmint.png?raw=true"
        st.markdown(f"""
        <div class="sidebar-logo">
            <img src="{logo_url}" style="height: 40px; border-radius: 6px;">
            <div class="sidebar-title">DocMint</div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("NEW TOOLS")
        if st.button("🗜️ Compress Docs"): st.session_state['current_tool'] = "Compress Docs"

        st.caption("IMAGE TOOLS")
        if st.button("📐 Resize Image"): st.session_state['current_tool'] = "Resize Image"
        if st.button("🎨 Image Editor"): st.session_state['current_tool'] = "Image Editor"
        if st.button("🔄 Convert Format"): st.session_state['current_tool'] = "Convert Format"
        if st.button("📑 JPG to PDF"): st.session_state['current_tool'] = "JPG to PDF"

        st.write("")
        st.caption("PDF TOOLS")
        if st.button("🔗 Merge PDF"): st.session_state['current_tool'] = "Merge PDF"
        if st.button("✂️ Split PDF"): st.session_state['current_tool'] = "Split PDF"
        if st.button("🖼️ PDF to JPG"): st.session_state['current_tool'] = "PDF to JPG"
        if st.button("📝 PDF Text"): st.session_state['current_tool'] = "PDF Text"
        
        st.write("")
        st.caption("OFFICE TOOLS")
        if st.button("📊 Merge PPTX"): st.session_state['current_tool'] = "Merge PPTX"

# --- 6. TOOLS (VERTICAL FLOW) ---

def tool_compress_docs():
    st.markdown(f"### 🗜️ Compress Documents")
    
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
                        st.download_button("⬇️ Download Result", res_buf.getvalue(), f"compressed_{uploaded.name}", "image/jpeg", type="primary")
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
                    st.success(f"✅ Done! New Size: {get_size_format(out.tell())}")
                    st.download_button("⬇️ Download PDF", out.getvalue(), f"compressed_{uploaded.name}", "application/pdf", type="primary")
                    st.markdown('</div>', unsafe_allow_html=True)

def tool_resize_image():
    st.markdown(f"### 📐 Resize Image")
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
            st.download_button("⬇️ Download Image", b.getvalue(), f"resized.{save_fmt.lower()}", f"image/{save_fmt.lower()}", type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

def tool_img_editor():
    st.markdown(f"### 🎨 Image Editor")
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
            st.download_button("⬇️ Download Image", b.getvalue(), f"edited.{fmt.lower()}", f"image/{fmt.lower()}", type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

def tool_merge_pdf():
    st.markdown(f"### 🔗 Merge PDFs")
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
            st.download_button("⬇️ Download Merged PDF", out.getvalue(), "merged.pdf", "application/pdf", type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

def tool_split_pdf():
    st.markdown(f"### ✂️ Split PDF")
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
                st.download_button("⬇️ Download Page", o.getvalue(), f"page_{p_num}.pdf", "application/pdf", type="primary")
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
                st.download_button("⬇️ Download ZIP", create_zip(files, "split.zip"), "split.zip", "application/zip", type="primary")
                st.markdown('</div>', unsafe_allow_html=True)

def tool_convert_format():
    st.markdown(f"### 🔄 Convert Format")
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
            st.download_button(f"⬇️ Download {target}", b.getvalue(), f"converted.{target.lower()}", mime, type="primary")
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
elif tool == "JPG to PDF":
    st.markdown("### 📑 JPG to PDF")
    u = st.file_uploader("Upload Images", type=["png", "jpg"], accept_multiple_files=True)
    if u and st.button("Create PDF", type="primary", use_container_width=True):
        imgs = [Image.open(f).convert("RGB") for f in u]
        b = BytesIO()
        imgs[0].save(b, "PDF", save_all=True, append_images=imgs[1:])
        st.markdown('<div class="result-box">', unsafe_allow_html=True)
        st.download_button("⬇️ Download PDF", b.getvalue(), "docmint_images.pdf", "application/pdf", type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Select a tool from the sidebar.")

st.markdown("---")
st.markdown("<div style='text-align:center; color:#94a3b8; font-size:0.8rem;'>© 2024 DocMint by Nitesh Kumar</div>", unsafe_allow_html=True)
