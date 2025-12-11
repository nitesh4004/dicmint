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
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE ---
if 'current_tool' not in st.session_state:
    st.session_state['current_tool'] = "Compress Docs" # Set new tool as default to show it off

# --- 3. CUSTOM CSS (Layout & Styling) ---
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

    /* Primary Button Style */
    .primary-btn {
        background-color: #007AFF !important;
        color: white !important;
    }

    /* Main Area Styling */
    .block-container {
        padding-top: 2rem;
    }

    /* Cards */
    .preview-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        min-height: 500px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .control-panel {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    
    h3 { font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; }
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
    """Iteratively adjusts quality/size to meet target KB"""
    target_bytes = target_kb * 1024
    
    # 1. First attempt: Reduce Quality (JPEG)
    low, high = 1, 95
    best_buffer = None
    
    # Binary search for quality
    while low <= high:
        mid = (low + high) // 2
        buf = BytesIO()
        # Convert to RGB if needed
        if img.mode in ("RGBA", "P"): 
            temp_img = img.convert("RGB")
        else:
            temp_img = img
            
        temp_img.save(buf, format="JPEG", quality=mid, optimize=True)
        size = buf.tell()
        
        if size <= target_bytes:
            best_buffer = buf
            low = mid + 1 # Try higher quality
        else:
            high = mid - 1 # Reduce quality
            
    if best_buffer:
        return best_buffer, "Quality Optimized"
        
    # 2. Second attempt: Resize Dimensions + Low Quality
    # If even quality=1 is too big, we must resize
    scale = 0.9
    width, height = img.size
    
    while scale > 0.1:
        new_w, new_h = int(width * scale), int(height * scale)
        buf = BytesIO()
        if img.mode in ("RGBA", "P"): temp_img = img.convert("RGB")
        else: temp_img = img
        
        resized = temp_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        resized.save(buf, format="JPEG", quality=50, optimize=True)
        
        if buf.tell() <= target_bytes:
            return buf, f"Resized to {int(scale*100)}%"
        scale -= 0.1
        
    return None, "Could not compress enough"

# --- 5. SIDEBAR NAVIGATION ---
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
        if st.button("🗜️ Compress Docs", use_container_width=True): st.session_state['current_tool'] = "Compress Docs"

        st.caption("IMAGE TOOLS")
        if st.button("📐 Resize Image", use_container_width=True): st.session_state['current_tool'] = "Resize Image"
        if st.button("🎨 Image Editor", use_container_width=True): st.session_state['current_tool'] = "Image Editor"
        if st.button("🔄 Convert Format", use_container_width=True): st.session_state['current_tool'] = "Convert Format"
        if st.button("📑 JPG to PDF", use_container_width=True): st.session_state['current_tool'] = "JPG to PDF"

        st.write("")
        st.caption("PDF TOOLS")
        if st.button("🔗 Merge PDF", use_container_width=True): st.session_state['current_tool'] = "Merge PDF"
        if st.button("✂️ Split PDF", use_container_width=True): st.session_state['current_tool'] = "Split PDF"
        if st.button("🖼️ PDF to JPG", use_container_width=True): st.session_state['current_tool'] = "PDF to JPG"
        if st.button("📝 PDF Text", use_container_width=True): st.session_state['current_tool'] = "PDF Text"
        
        st.write("")
        st.caption("OFFICE TOOLS")
        if st.button("📊 Merge PPTX", use_container_width=True): st.session_state['current_tool'] = "Merge PPTX"

# --- 6. TOOL LOGIC ---

def tool_compress_docs():
    st.markdown(f"### 🗜️ {st.session_state['current_tool']}")
    col_controls, col_preview = st.columns([1, 2], gap="large")
    
    with col_controls:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        st.markdown("#### Select Document Type")
        doc_type = st.radio("Type", ["Image (Target Size)", "PDF (Reduce Size)"])
        
        if doc_type == "Image (Target Size)":
            uploaded = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"], key="comp_img")
            if uploaded:
                current_size = uploaded.size / 1024 # KB
                st.caption(f"Current Size: {current_size:.1f} KB")
                
                target_kb = st.number_input("Target Size (KB)", min_value=10, max_value=int(current_size), value=int(current_size*0.8))
                comp_btn = st.button("Compress Image", type="primary", use_container_width=True)

        else: # PDF
            uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="comp_pdf")
            if uploaded:
                st.caption(f"Current Size: {get_size_format(uploaded.size)}")
                level = st.select_slider("Compression Level", options=["Low", "Medium", "High"], value="Medium")
                comp_btn = st.button("Compress PDF", type="primary", use_container_width=True)
                
        st.markdown('</div>', unsafe_allow_html=True)

    with col_preview:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        if uploaded:
            if doc_type == "Image (Target Size)":
                img = Image.open(uploaded)
                st.image(img, caption="Original", width=300)
                
                if 'comp_btn' in locals() and comp_btn:
                    with st.spinner("Calculating optimal compression..."):
                        res_buf, method = compress_image_to_target(img, target_kb)
                        
                        if res_buf:
                            new_size = res_buf.tell() / 1024
                            st.success(f"✅ Achieved: {new_size:.1f} KB ({method})")
                            st.download_button("⬇️ Download Compressed", res_buf.getvalue(), f"compressed_{uploaded.name}", "image/jpeg", type="primary")
                        else:
                            st.error("Target too low. Cannot compress further without destroying image.")
                            
            else: # PDF
                st.write(f"📄 **{uploaded.name}**")
                if 'comp_btn' in locals() and comp_btn:
                    with st.spinner("Compressing PDF structure..."):
                        reader = PdfReader(uploaded)
                        writer = PdfWriter()
                        
                        for page in reader.pages:
                            if level in ["Medium", "High"]:
                                page.compress_content_streams() # Lossless compression
                            writer.add_page(page)
                            
                        # High compression metadata stripping logic could go here
                        if level == "High":
                            writer.add_metadata({}) # Strip metadata
                            
                        out = BytesIO()
                        writer.write(out)
                        new_size = out.tell()
                        
                        st.success(f"✅ Done! New Size: {get_size_format(new_size)}")
                        st.download_button("⬇️ Download PDF", out.getvalue(), f"compressed_{uploaded.name}", "application/pdf", type="primary")
        else:
            st.info("Upload a file to start compressing.")
        st.markdown('</div>', unsafe_allow_html=True)

def tool_resize_image():
    st.markdown(f"### 📐 {st.session_state['current_tool']}")
    col_controls, col_preview = st.columns([1, 2], gap="large")
    
    with col_controls:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp"], key="resize_upl")
        
        img = None
        if uploaded:
            img = Image.open(uploaded)
            st.markdown(f"<small>Original: {img.width}x{img.height}</small>", unsafe_allow_html=True)
            
            unit = st.radio("Unit", ["Pixels", "Percent"], horizontal=True)
            lock = st.checkbox("Lock Aspect Ratio", value=True)
            
            if unit == "Pixels":
                w = st.number_input("Width", value=img.width, step=1)
                if lock:
                    ratio = img.height / img.width
                    h = int(w * ratio)
                    st.number_input("Height", value=h, disabled=True)
                else:
                    h = st.number_input("Height", value=img.height, step=1)
            else:
                pct = st.slider("Percentage", 1, 200, 100)
                w = int(img.width * (pct/100))
                h = int(img.height * (pct/100))
                st.caption(f"Output: {w} x {h} px")

            st.markdown("#### Export")
            fmt = st.selectbox("Format", ["JPG", "PNG", "WEBP"], index=0)
            process_btn = st.button("⚡ Process Image", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_preview:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        if img:
            st.image(img, caption="Preview", width=400)
            if 'process_btn' in locals() and process_btn:
                new_img = img.resize((w, h), Image.Resampling.LANCZOS)
                b = BytesIO()
                save_fmt = "JPEG" if fmt == "JPG" else fmt
                if save_fmt == "JPEG" and new_img.mode in ("RGBA", "P"): new_img = new_img.convert("RGB")
                new_img.save(b, format=save_fmt, quality=95)
                
                st.markdown("---")
                st.success("Resized!")
                st.download_button(f"⬇️ Download {fmt}", b.getvalue(), f"resized.{save_fmt.lower()}", f"image/{save_fmt.lower()}", type="primary")
        else:
            st.info("Upload on left to preview.")
        st.markdown('</div>', unsafe_allow_html=True)

def tool_img_editor():
    st.markdown(f"### 🎨 {st.session_state['current_tool']}")
    col_controls, col_preview = st.columns([1, 2], gap="large")
    
    with col_controls:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload", type=["png", "jpg"], key="edit_upl")
        img = None
        if uploaded:
            img = Image.open(uploaded)
            angle = st.slider("Rotation", 0, 360, 0)
            filt = st.selectbox("Filter", ["None", "Grayscale", "Blur", "Sharpen", "Contour"])
        st.markdown('</div>', unsafe_allow_html=True)

    with col_preview:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        if img:
            processed = img.copy()
            if angle: processed = processed.rotate(angle, expand=True)
            if filt == "Grayscale": processed = ImageOps.grayscale(processed)
            elif filt == "Blur": processed = processed.filter(ImageFilter.BLUR)
            elif filt == "Sharpen": processed = processed.filter(ImageFilter.SHARPEN)
            elif filt == "Contour": processed = processed.filter(ImageFilter.CONTOUR)
            
            st.image(processed, caption="Live Edit", width=400)
            b = BytesIO()
            fmt = img.format if img.format else "PNG"
            processed.save(b, format=fmt)
            st.download_button("⬇️ Download", b.getvalue(), f"edited.{fmt.lower()}", f"image/{fmt.lower()}", type="primary")
        else: st.write("Waiting for image...")
        st.markdown('</div>', unsafe_allow_html=True)

def tool_merge_pdf():
    st.markdown(f"### 🔗 {st.session_state['current_tool']}")
    col_controls, col_preview = st.columns([1, 2], gap="large")
    with col_controls:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        files = st.file_uploader("Select PDFs", type="pdf", accept_multiple_files=True)
        file_map = {}
        if files:
            file_map = {f.name: f for f in files}
            order = st.multiselect("Reorder", list(file_map.keys()), default=list(file_map.keys()))
            merge_btn = st.button("Merge", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_preview:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        if files and 'merge_btn' in locals() and merge_btn:
            merger = PdfWriter()
            for name in order: merger.append(file_map[name])
            out = BytesIO()
            merger.write(out)
            st.success("Merged!")
            st.download_button("⬇️ Download", out.getvalue(), "merged.pdf", "application/pdf", type="primary")
        else: st.info("Upload PDFs to merge.")
        st.markdown('</div>', unsafe_allow_html=True)

def tool_split_pdf():
    st.markdown(f"### ✂️ {st.session_state['current_tool']}")
    col_controls, col_preview = st.columns([1, 2], gap="large")
    with col_controls:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        f = st.file_uploader("Upload PDF", type="pdf")
        if f:
            reader = PdfReader(f)
            total = len(reader.pages)
            mode = st.radio("Mode", ["Extract One", "Split All"])
            if mode == "Extract One": p_num = st.number_input("Page #", 1, total, 1)
            btn = st.button("Process", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_preview:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        if f and 'btn' in locals() and btn:
            if mode == "Extract One":
                w = PdfWriter()
                w.add_page(reader.pages[p_num-1])
                o = BytesIO()
                w.write(o)
                st.download_button("⬇️ Download Page", o.getvalue(), f"page_{p_num}.pdf", "application/pdf")
            else:
                files = {}
                for i in range(total):
                    w = PdfWriter()
                    w.add_page(reader.pages[i])
                    o = BytesIO()
                    w.write(o)
                    files[f"page_{i+1}.pdf"] = o.getvalue()
                st.download_button("⬇️ Download ZIP", create_zip(files, "split.zip"), "split.zip", "application/zip")
        else: st.info("Upload PDF to split.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 7. DISPATCHER & MAIN ---

render_sidebar()
tool = st.session_state['current_tool']

if tool == "Compress Docs": tool_compress_docs()
elif tool == "Resize Image": tool_resize_image()
elif tool == "Image Editor": tool_img_editor()
elif tool == "Merge PDF": tool_merge_pdf()
elif tool == "Split PDF": tool_split_pdf()
elif tool == "Convert Format":
    st.markdown(f"### 🔄 {tool}")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        u = st.file_uploader("Upload", type=["png", "jpg", "webp"])
        t = st.selectbox("Target", ["PNG", "JPEG", "PDF", "WEBP"])
        if u: st.button("Convert", type="primary", key="conv_btn")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        if u and st.session_state.get("conv_btn"):
            i = Image.open(u)
            if t == "JPEG" and i.mode == "RGBA": i = i.convert("RGB")
            b = BytesIO()
            i.save(b, format=t)
            st.download_button("Download", b.getvalue(), f"conv.{t.lower()}", f"image/{t.lower()}", type="primary")
        else: st.info("Waiting for upload.")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # Fallback for tools not fully detailed in this update, but structure exists
    st.info("Select a tool from the sidebar.")

st.markdown("---")
st.markdown("<div style='text-align:center; color:#94a3b8; font-size:0.8rem;'>© 2024 DocMint by Nitesh Kumar</div>", unsafe_allow_html=True)
