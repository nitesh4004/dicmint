import streamlit as st
import os
from io import BytesIO
import zipfile
from PIL import Image, ImageOps, ImageFilter

# PDF Libraries
from PyPDF2 import PdfReader, PdfWriter

# PPT Libraries
from pptx import Presentation

# PDF to Image (Requires Poppler System Dependency)
try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False
except Exception:
    HAS_PDF2IMAGE = False

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DocMint - Free Document Tools",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. SESSION STATE MANAGEMENT ---
if 'current_tool' not in st.session_state:
    st.session_state['current_tool'] = "Home"

def navigate_to(tool_name):
    st.session_state['current_tool'] = tool_name

def go_home():
    st.session_state['current_tool'] = "Home"

# --- 3. CUSTOM CSS (UI/UX & THEME COMPATIBILITY) ---
st.markdown("""
<style>
    /* Global Text Visibility Fix */
    body, .stMarkdown, .stButton, p, h1, h2, h3 {
        color: inherit !important;
    }

    /* Navbar Styling */
    .nav-container {
        background: linear-gradient(90deg, #2E7D32, #4CAF50); /* Minty Green Theme */
        padding: 1.5rem;
        border-radius: 0 0 15px 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .logo-container {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .app-title {
        font-size: 2rem;
        font-weight: 800;
        color: white !important;
        margin: 0;
        line-height: 1.2;
    }
    
    .app-subtitle {
        font-size: 1.1rem;
        font-weight: 400;
        color: rgba(255,255,255,0.9) !important;
    }

    /* Tool Cards (Grid Buttons) - Adaptive Theme */
    div.stButton > button {
        background-color: var(--secondary-background-color);
        color: var(--text-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 15px;
        padding: 20px 10px;
        height: 100%;
        width: 100%;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 140px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Hover Effect */
    div.stButton > button:hover {
        border-color: #4CAF50;
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(76, 175, 80, 0.2);
        color: #4CAF50 !important;
    }

    /* Action Buttons (Submit/Download) */
    div.stDownloadButton > button, div.stFormSubmitButton > button {
        background-color: #2E7D32 !important;
        color: white !important;
        border: none !important;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.6rem 1rem;
    }
    
    div.stDownloadButton > button:hover, div.stFormSubmitButton > button:hover {
        background-color: #1B5E20 !important;
        color: white !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: var(--secondary-background-color);
        border-radius: 10px 10px 0 0;
        padding: 0 20px;
        border: 1px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2E7D32 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. HELPER FUNCTIONS ---
def create_zip(files_dict, zip_name):
    """Packs a dictionary of filename:bytes into a zip file"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file_name, data in files_dict.items():
            zip_file.writestr(file_name, data)
    return zip_buffer.getvalue()

# --- 5. UI RENDERERS ---

def render_header():
    """Renders the Header with Branding and Navigation"""
    tool_display = st.session_state['current_tool']
    
    # Using raw=true to ensure image loads directly
    logo_url = "https://github.com/nitesh4004/Ni30-pdflover/blob/main/docmint.png?raw=true"
    
    # Custom HTML Header
    st.markdown(f"""
    <div class="nav-container">
        <div class="logo-container">
            <img src="{logo_url}" alt="DocMint Logo" style="height: 60px; width: auto; border-radius: 8px;">
            <div>
                <p class="app-title">DocMint</p>
            </div>
        </div>
        <div>
            <p class="app-subtitle">{tool_display if tool_display != "Home" else "Fresh tools for your docs"}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Back Button Logic
    if st.session_state['current_tool'] != "Home":
        if st.button("⬅ Back to Dashboard", key="home_btn"):
            go_home()
            st.rerun()
        st.markdown("---")

def render_tool_card(tool_info, col):
    """Helper to render a single tool card inside a column"""
    with col:
        label = f"{tool_info['icon']}\n\n{tool_info['name']}"
        if st.button(label, key=tool_info['id'], use_container_width=True, help=tool_info['desc']):
            navigate_to(tool_info['name'])
            st.rerun()

def render_home():
    """Renders the Dashboard with Tabs"""
    
    # Define Tools by Category
    pdf_tools = [
        {"name": "Merge PDF", "icon": "🔗", "desc": "Combine PDFs in specific order.", "id": "merge_pdf"},
        {"name": "Split PDF", "icon": "✂️", "desc": "Separate pages.", "id": "split_pdf"},
        {"name": "PDF to JPG", "icon": "🖼️", "desc": "Convert PDF pages to images.", "id": "pdf_to_img"},
        {"name": "PDF Text", "icon": "📝", "desc": "Extract text data.", "id": "pdf_text"},
    ]
    
    img_tools = [
        {"name": "Image Editor", "icon": "🎨", "desc": "Crop, rotate, filter.", "id": "img_editor"},
        {"name": "Img Convert", "icon": "🔄", "desc": "Change format (PNG/JPG).", "id": "img_convert"},
        {"name": "JPG to PDF", "icon": "📑", "desc": "Images to PDF.", "id": "img_to_pdf"},
    ]
    
    ppt_tools = [
        {"name": "Merge PPTX", "icon": "📊", "desc": "Combine slides.", "id": "merge_pptx"},
        {"name": "PPTX Text", "icon": "📄", "desc": "Read presentation text.", "id": "pptx_text"},
    ]

    # Tabs Layout
    tab1, tab2, tab3 = st.tabs(["📄 PDF Tools", "🖼️ Image Tools", "📊 PPT & Others"])

    with tab1:
        st.caption("Manipulate your PDF documents.")
        cols = st.columns(4)
        for i, tool in enumerate(pdf_tools):
            render_tool_card(tool, cols[i % 4])

    with tab2:
        st.caption("Edit and convert your images.")
        cols = st.columns(4)
        for i, tool in enumerate(img_tools):
            render_tool_card(tool, cols[i % 4])
            
    with tab3:
        st.caption("PowerPoint and other utilities.")
        cols = st.columns(4)
        for i, tool in enumerate(ppt_tools):
            render_tool_card(tool, cols[i % 4])

# --- 6. TOOL LOGIC ---

def tool_merge_pdf():
    st.info("Combine multiple PDFs into one. Reorder them using the list below.")
    uploaded_pdfs = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    
    if uploaded_pdfs:
        # Create a mapping of Name -> FileObject
        file_map = {file.name: file for file in uploaded_pdfs}
        file_names = list(file_map.keys())
        
        st.write("### ↕️ Set Order")
        st.write("Select the files in the order you want them to appear in the final PDF. You can drag tags to reorder.")
        
        selected_order = st.multiselect(
            "File Order (Left is first, Right is last):", 
            options=file_names, 
            default=file_names
        )
        
        if len(selected_order) > 0:
            if st.button("Merge Files"):
                with st.spinner("Merging in progress..."):
                    merger = PdfWriter()
                    for name in selected_order:
                        merger.append(file_map[name])
                    
                    output = BytesIO()
                    merger.write(output)
                    st.success("✅ PDF Merged Successfully!")
                    st.download_button(
                        label="Download Merged PDF", 
                        data=output.getvalue(), 
                        file_name="docmint_merged.pdf", 
                        mime="application/pdf"
                    )

def tool_split_pdf():
    st.info("Split a PDF into single pages or extract specific ones.")
    uploaded_pdf = st.file_uploader("Upload PDF", type="pdf")
    
    if uploaded_pdf:
        reader = PdfReader(uploaded_pdf)
        total_pages = len(reader.pages)
        st.write(f"**Total Pages Detected:** {total_pages}")
        
        mode = st.radio("Select Action:", ["Extract Specific Page", "Split All Pages into ZIP"])
        
        if mode == "Extract Specific Page":
            page_num = st.number_input("Enter Page Number", 1, total_pages, 1)
            if st.button("Download Page"):
                writer = PdfWriter()
                writer.add_page(reader.pages[page_num-1])
                out = BytesIO()
                writer.write(out)
                st.download_button(f"Download Page {page_num}", out.getvalue(), f"page_{page_num}.pdf", "application/pdf")
        else:
            if st.button("Process & Download ZIP"):
                files = {}
                for i in range(total_pages):
                    w = PdfWriter()
                    w.add_page(reader.pages[i])
                    o = BytesIO()
                    w.write(o)
                    files[f"page_{i+1}.pdf"] = o.getvalue()
                
                zip_data = create_zip(files, "docmint_split.zip")
                st.download_button("Download ZIP File", zip_data, "docmint_split.zip", "application/zip")

def tool_pdf_to_img():
    if not HAS_PDF2IMAGE:
        st.error("⚠️ System dependency 'Poppler' is missing. This tool works best on local setups with Poppler installed.")
        return
        
    st.info("Convert PDF pages into high-quality JPG images.")
    uploaded_pdf = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_pdf:
        if st.button("Convert to Images"):
            with st.spinner("Processing pages..."):
                try:
                    images = convert_from_bytes(uploaded_pdf.read())
                    files = {}
                    for i, img in enumerate(images):
                        b = BytesIO()
                        img.save(b, format="JPEG")
                        files[f"page_{i+1}.jpg"] = b.getvalue()
                    
                    zip_data = create_zip(files, "docmint_images.zip")
                    st.success(f"Successfully converted {len(images)} pages.")
                    st.download_button("Download Images (ZIP)", zip_data, "docmint_images.zip", "application/zip")
                except Exception as e:
                    st.error(f"Error processing file: {e}")

def tool_img_editor():
    st.info("Upload an image to edit.")
    uploaded = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    if uploaded:
        img = Image.open(uploaded)
        col1, col2 = st.columns(2)
        with col1:
            st.image(img, use_container_width=True, caption="Original")
        
        with st.form("edit_form"):
            st.write("### Edit Options")
            c1, c2 = st.columns(2)
            with c1:
                angle = st.slider("Rotate (Degrees)", 0, 360, 0)
                filter_t = st.selectbox("Apply Filter", ["None", "Grayscale", "Blur", "Sharpen", "Contour"])
            with c2:
                new_w = st.number_input("Target Width (px)", value=img.width)
                new_h = st.number_input("Target Height (px)", value=img.height)
            
            resize_check = st.checkbox("Apply Resize Dimensions")
            submitted = st.form_submit_button("Apply Changes")
            
        if submitted:
            processed = img.copy()
            if resize_check:
                processed = processed.resize((int(new_w), int(new_h)))
            if angle != 0:
                processed = processed.rotate(angle, expand=True)
            
            if filter_t == "Grayscale": processed = ImageOps.grayscale(processed)
            elif filter_t == "Blur": processed = processed.filter(ImageFilter.BLUR)
            elif filter_t == "Sharpen": processed = processed.filter(ImageFilter.SHARPEN)
            elif filter_t == "Contour": processed = processed.filter(ImageFilter.CONTOUR)
            
            with col2:
                st.image(processed, use_container_width=True, caption="Edited Result")
                b = BytesIO()
                fmt = img.format if img.format else "PNG"
                processed.save(b, format=fmt)
                st.download_button("Download Image", b.getvalue(), f"edited_image.{fmt.lower()}", f"image/{fmt.lower()}")

def tool_img_convert():
    st.info("Convert image formats easily.")
    uploaded = st.file_uploader("Upload Image", type=["png", "jpg", "tiff", "bmp", "webp"])
    if uploaded:
        img = Image.open(uploaded)
        st.write(f"Current Format: **{img.format}**")
        target = st.selectbox("Convert To:", ["PNG", "JPEG", "PDF", "WEBP", "ICO"])
        
        if st.button("Convert File"):
            b = BytesIO()
            img_s = img.copy()
            if target == "JPEG" and img_s.mode in ("RGBA", "P"): 
                img_s = img_s.convert("RGB")
            
            save_fmt = "JPEG" if target == "JPEG" else target
            img_s.save(b, format=save_fmt)
            
            mime_type = "application/pdf" if target == "PDF" else f"image/{target.lower()}"
            st.download_button(f"Download as {target}", b.getvalue(), f"converted.{target.lower()}", mime_type)

def tool_img_to_pdf():
    st.info("Merge multiple images into a single PDF file.")
    uploads = st.file_uploader("Select Images", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    if uploads:
        file_map = {f.name: f for f in uploads}
        order = st.multiselect("Set Image Order:", list(file_map.keys()), default=list(file_map.keys()))
        
        if st.button("Generate PDF") and order:
            imgs = []
            for name in order:
                i = Image.open(file_map[name])
                if i.mode == "RGBA": i = i.convert("RGB")
                imgs.append(i)
            
            if imgs:
                b = BytesIO()
                imgs[0].save(b, "PDF", save_all=True, append_images=imgs[1:])
                st.success("PDF Created!")
                st.download_button("Download PDF", b.getvalue(), "docmint_merged.pdf", "application/pdf")

def tool_merge_pptx():
    st.info("Merge slides from multiple PowerPoint files sequentially.")
    uploads = st.file_uploader("Upload PPTX files", type="pptx", accept_multiple_files=True)
    if uploads:
        file_map = {f.name: f for f in uploads}
        order = st.multiselect("Set Slide Deck Order:", list(file_map.keys()), default=list(file_map.keys()))
        
        if st.button("Merge Presentations") and order:
            try:
                out_prs = Presentation()
                xml = out_prs.slides._sldIdLst
                sl = list(xml)
                if sl: xml.remove(sl[0])
                
                for name in order:
                    in_prs = Presentation(file_map[name])
                    for s in in_prs.slides:
                        layout = out_prs.slide_layouts[6] 
                        dest = out_prs.slides.add_slide(layout)
                        for sh in s.shapes:
                            if hasattr(sh, "text"):
                                try:
                                    tb = dest.shapes.add_textbox(sh.left, sh.top, sh.width, sh.height)
                                    tb.text_frame.text = sh.text
                                except: pass
                b = BytesIO()
                out_prs.save(b)
                st.success("Merged successfully.")
                st.download_button("Download PPTX", b.getvalue(), "docmint_merged.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
            except Exception as e:
                st.error(f"Merge Error: {e}")

def tool_pdf_text():
    st.info("Extract raw text from PDF for editing.")
    f = st.file_uploader("Select PDF", type="pdf")
    if f:
        r = PdfReader(f)
        if st.button("Extract Text"):
            text = ""
            for i, p in enumerate(r.pages):
                text += f"--- Page {i+1} ---\n{p.extract_text()}\n\n"
            st.text_area("Extracted Content", text, height=300)
            st.download_button("Download .txt", text, "extracted.txt", "text/plain")

def tool_pptx_text():
    st.info("Extract text content from PowerPoint slides.")
    f = st.file_uploader("Select PPTX", type="pptx")
    if f:
        if st.button("Extract Text"):
            p = Presentation(f)
            text_list = []
            for i, s in enumerate(p.slides):
                t = [sh.text for sh in s.shapes if hasattr(sh, "text")]
                text_list.append(f"--- Slide {i+1} ---\n" + "\n".join(t))
            full_text = "\n\n".join(text_list)
            st.text_area("Extracted Content", full_text, height=300)
            st.download_button("Download .txt", full_text, "slides.txt", "text/plain")

# --- 7. MAIN APP ROUTING ---

render_header()

tool = st.session_state['current_tool']

if tool == "Home":
    render_home()
elif tool == "Merge PDF":
    tool_merge_pdf()
elif tool == "Split PDF":
    tool_split_pdf()
elif tool == "PDF to JPG":
    tool_pdf_to_img()
elif tool == "PDF Text":
    tool_pdf_text()
elif tool == "Image Editor":
    tool_img_editor()
elif tool == "Img Convert":
    tool_img_convert()
elif tool == "JPG to PDF":
    tool_img_to_pdf()
elif tool == "Merge PPTX":
    tool_merge_pptx()
elif tool == "PPTX Text":
    tool_pptx_text()

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8rem; padding: 20px;'>© 2024 DocMint | Secure Browser Processing</div>", unsafe_allow_html=True)
