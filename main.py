import os 
from dotenv import load_dotenv
import pandas as pd 
import time
import streamlit as st
from datetime import datetime
import tempfile
import io
import traceback
import logging
import gc
import warnings
import base64
import hashlib
import json
import os
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import gc
import fitz
from openai import OpenAI


warnings.filterwarnings('ignore', category=RuntimeWarning)
logging.getLogger('streamlit.watcher.local_sources_watcher').setLevel(logging.ERROR)

st.set_page_config(
    page_title="Alphamed PDF Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Current PATH: {os.environ.get('PATH')}")
logger.info(f"Current working directory: {os.getcwd()}")

load_dotenv()
# groq_api_key = os.getenv("GROQ_API_KEY")
# groq_client = Groq(api_key=groq_api_key)
# print(os.environ['PATH'])
# 
open_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=open_api_key)

def admin_tracking_tab():
    st.info("User tracking is disabled.")


def display_excel_native(excel_data):
    """Display Excel data using native Streamlit components with persistent editing"""
    try:
        df = pd.read_excel(io.BytesIO(excel_data))

        excel_file = io.BytesIO(excel_data)
        xl = pd.ExcelFile(excel_file)
        sheet_names = xl.sheet_names

        if len(sheet_names) > 1:
            selected_sheet = st.selectbox("Select Sheet:", sheet_names)
            df = pd.read_excel(excel_file, sheet_name=selected_sheet)

        session_key = f"edited_df_{datetime.now().strftime('%Y%m%d')}"
        
        if session_key not in st.session_state:
            st.session_state[session_key] = df.copy()
        
        edited_df = st.data_editor(
            st.session_state[session_key],
            use_container_width=True,
            num_rows="dynamic",
            height=600,
            key=f'grid_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            column_config={col: st.column_config.Column(
                width="auto",
                help=f"Column: {col}"
            ) for col in df.columns}
        )
        
        st.session_state[session_key] = edited_df
        
        search = st.text_input("🔍 Search in table:", key="search_input")
        if search:
            mask = edited_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            filtered_df = edited_df[mask]
        else:
            filtered_df = edited_df
            
        st.markdown(f"**Total Rows:** {len(filtered_df)} | **Total Columns:** {len(filtered_df.columns)}")
        
        if st.button("💾 Save Changes", key="save_changes"):
            try:
                st.session_state.saved_df = edited_df.copy()
                
                save_path = save_uploaded_files(
                    st.session_state.username,
                    st.session_state.uploaded_pdfs,
                    st.session_state.saved_df
                )
                
                if save_path:
                    st.success("✅ Changes saved successfully!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            edited_df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 Download Edited Excel",
                            data=buffer.getvalue(),
                            file_name="edited_data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_edited"
                        )
                    
                    with col2:
                        buffer_original = io.BytesIO()
                        with pd.ExcelWriter(buffer_original, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 Download Original Excel",
                            data=buffer_original.getvalue(),
                            file_name="original_data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_original"
                        )
            
            except Exception as e:
                st.error(f"Error saving changes: {str(e)}")
        
        return edited_df
        
    except Exception as e:
        st.error(f"Error displaying Excel file: {str(e)}")
        return None

def cleanup_temp_files():
    """Clean up any leftover temporary files"""
    if 'cleanup_files' in st.session_state:
        for tmp_path in st.session_state.cleanup_files[:]:  
            try:
                if os.path.exists(tmp_path):
                    gc.collect() 
                    os.unlink(tmp_path)
                st.session_state.cleanup_files.remove(tmp_path)
            except Exception:
                pass  

# def process_uploaded_files(pdfs_to_process):
#     """Process uploaded PDF files with enhanced handling for large files"""
#     try:
#         if st.session_state.edited_df is not None:
            
#             edited_df = display_excel_native(pd.DataFrame(st.session_state.edited_df))
#             if edited_df is not None:
#                 st.session_state.edited_df = edited_df
#         else:
            
#             progress_bar = st.progress(0)
#             status_text = st.empty()
            
#             total_files = len(pdfs_to_process)
#             total_rows_processed = 0
#             total_pages_processed = 0
#             all_data = []
#             all_headers = None
            
#             for idx, uploaded_pdf_file in enumerate(pdfs_to_process):
#                 try:
#                     status_text.text(f"Processing file {idx + 1} of {total_files}: {uploaded_pdf_file.name}")
                    
#                     with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#                         tmp_file.write(uploaded_pdf_file.getvalue())
#                         tmp_path = tmp_file.name
                        

#                         try:
#                             with fitz.open(tmp_path) as pdf_doc:
#                                 file_pages = len(pdf_doc)
#                                 st.write(f"Pages in {uploaded_pdf_file.name}: {file_pages}")  # Debug output
#                                 total_pages_processed += file_pages
#                         except Exception as e:
#                             st.error(f"Error counting pages in {uploaded_pdf_file.name}: {str(e)}")
#                             file_pages = 0
                        
#                         with st.spinner(f"Extracting text from {uploaded_pdf_file.name}..."):
#                             pdf_text = extract_text_pdf(tmp_path)

                            
#                             if pdf_text:
#                                 with st.spinner("Processing extracted text..."):
#                                     estimated_tokens = len(pdf_text) // 3
#                                     if estimated_tokens > 6000:
#                                         st.info(f"Large document detected ({estimated_tokens} est. tokens). Processing in chunks...")
                                    
#                                     invoice_info = using_groq(pdf_text)
#                                     rows_in_file = count_processed_rows(invoice_info)
#                                     total_rows_processed += rows_in_file
                                    
#                                     headers, data_rows = process_invoice_lines(
#                                         invoice_info, 
 
#                                     )
                                    
#                                     if headers and data_rows:
#                                         if all_headers is None:
#                                             all_headers = headers
                                        
#                                         all_data.extend(data_rows)
                        
#                         try:
#                             os.unlink(tmp_path)
#                         except Exception as e:
#                             st.warning(f"Could not remove temporary file: {str(e)}")
#                             if 'cleanup_files' not in st.session_state:
#                                 st.session_state.cleanup_files = []
#                             st.session_state.cleanup_files.append(tmp_path)
                        
#                 except Exception as e:
#                     st.error(f"Error processing {uploaded_pdf_file.name}: {str(e)}")
                
#                 progress_bar.progress((idx + 1) / total_files)
#                 gc.collect()
            
#             if all_data and all_headers:
#                 df = pd.DataFrame(all_data, columns=all_headers)
#                 st.session_state.edited_df = df.copy()
                
#                 edited_df = display_excel_native(df)
#                 if edited_df is not None:
#                     st.session_state.edited_df = edited_df
#             else:
#                 st.error("No valid data could be extracted from the invoices")
            
#             update_user_tracking(
#                 username=st.session_state.username,
#                 files_uploaded=total_files,
#                 rows_processed=total_rows_processed,
#                 pages_processed=total_pages_processed
#             )
    
#     except Exception as e:
#         st.error(f"Error processing files: {str(e)}")
#         st.error(traceback.format_exc())


def process_uploaded_files(pdfs_to_process):
    """Process uploaded PDF files with enhanced handling for large files and proper page counting"""
    try:
        if st.session_state.edited_df is not None:
            edited_df = display_excel_native(pd.DataFrame(st.session_state.edited_df))
            if edited_df is not None:
                st.session_state.edited_df = edited_df
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_files = len(pdfs_to_process)
            total_rows_processed = 0
            total_pages_processed = 0
            all_data = []
            all_headers = None
            
            page_count_container = st.empty()
            
            for idx, uploaded_pdf_file in enumerate(pdfs_to_process):
                try:
                    status_text.text(f"Processing file {idx + 1} of {total_files}: {uploaded_pdf_file.name}")
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_pdf_file.getvalue())
                        tmp_path = tmp_file.name
                        
                        # Count pages and add to total
                        file_pages = count_pdf_pages(tmp_path)
                        total_pages_processed += file_pages
                        page_count_container.info(f"Total pages processed: {total_pages_processed}")
                        
                        with st.spinner(f"Extracting text from {uploaded_pdf_file.name}..."):
                            pdf_text = extract_text_pdf(tmp_path)
                            
                            if pdf_text:
                                with st.spinner("Processing extracted text..."):
                                    estimated_tokens = len(pdf_text) // 3
                                    if estimated_tokens > 6000:
                                        st.info(f"Large document detected ({estimated_tokens} est. tokens). Processing in chunks...")
                                    
                                    invoice_info = using_groq(pdf_text)
                                    rows_in_file = count_processed_rows(invoice_info)
                                    total_rows_processed += rows_in_file
                                    
                                    headers, data_rows = process_invoice_lines(
                                        invoice_info
                                    )
                                    
                                    if headers and data_rows:
                                        if all_headers is None:
                                            all_headers = headers
                                        
                                        all_data.extend(data_rows)
                        
                        try:
                            os.unlink(tmp_path)
                        except Exception as e:
                            st.warning(f"Could not remove temporary file: {str(e)}")
                            if 'cleanup_files' not in st.session_state:
                                st.session_state.cleanup_files = []
                            st.session_state.cleanup_files.append(tmp_path)
                        
                except Exception as e:
                    st.error(f"Error processing {uploaded_pdf_file.name}: {str(e)}")
                
                progress_bar.progress((idx + 1) / total_files)
                gc.collect()
            
            if all_data and all_headers:
                df = pd.DataFrame(all_data, columns=all_headers)
                st.session_state.edited_df = df.copy()
                
                edited_df = display_excel_native(df)
                if edited_df is not None:
                    st.session_state.edited_df = edited_df
            else:
                st.error("No valid data could be extracted from the invoices")
            
            
    
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.error(traceback.format_exc())

def update_user_tracking(username, files_uploaded=0, rows_processed=0, pages_processed=0):
    return

def count_pdf_pages(pdf_path):
    """Count pages in a PDF file with robust error handling"""
    try:
        with fitz.open(pdf_path) as pdf_doc:
            return len(pdf_doc)
    except Exception as e:
        st.warning(f"Could not count pages automatically: {str(e)}")
        return 0


def create_editable_grid(df, key_prefix=""):
    """
    Create an editable grid using Streamlit data editor
    """
    try:
        column_config = {
            col: st.column_config.Column(
                width="auto",
                help=f"Edit {col}"
            ) for col in df.columns
        }
        
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            column_config=column_config,
            key=f"{key_prefix}_grid_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            height=600
        )
        
        search_term = st.text_input(
            "🔍 Search in table:",
            key=f"{key_prefix}_search_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        if search_term:
            
            mask = edited_df.astype(str).apply(
                lambda x: x.str.contains(search_term, case=False)
            ).any(axis=1)
            filtered_df = edited_df[mask]
        else:
            filtered_df = edited_df
            
        st.markdown(f"**Total Rows:** {len(filtered_df)} | **Total Columns:** {len(filtered_df.columns)}")
        
        return edited_df, filtered_df
        
    except Exception as e:
        st.error(f"Error in create_editable_grid: {str(e)}")
        return df, df


def display_extracted_data(df):
    """Display and manage editable extracted data with persistent state"""
    try:
        st.markdown("### 📝 Extracted and Edited Data")
        
        if 'grid_key' not in st.session_state:
            st.session_state.grid_key = 'data_editor_1'
        if 'editor_data' not in st.session_state:
            st.session_state.editor_data = df.copy()
        
        search_query = st.text_input("🔍 Search in table:", key="search_input")
        
        display_data = st.session_state.editor_data.copy()
        if search_query:
            mask = display_data.astype(str).apply(
                lambda x: x.str.contains(search_query, case=False)
            ).any(axis=1)
            display_data = display_data[mask]
        
        edited_df = st.data_editor(
            display_data,
            use_container_width=True,
            num_rows="dynamic",
            key=st.session_state.grid_key,
            height=600,
            column_config={
                col: st.column_config.Column(
                    width="auto",
                    help=f"Edit {col}"
                ) for col in df.columns
            }
        )
        
        st.session_state.editor_data = edited_df
        st.markdown(f"**Total Rows:** {len(edited_df)} | **Total Columns:** {len(edited_df.columns)}")
        
        if st.button("💾 Save Changes", key="save_changes"):
            try:
                st.session_state.saved_df = edited_df.copy()
                st.session_state.edited_df = edited_df.copy()
                
                save_path = save_uploaded_files(
                    st.session_state.username,
                    st.session_state.uploaded_pdfs,
                    st.session_state.saved_df
                )
                
                if save_path:
                    st.success("✅ Changes saved successfully!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            edited_df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 Download Edited Excel",
                            data=buffer.getvalue(),
                            file_name="edited_data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_edited"
                        )
                    
                    with col2:
                        buffer_original = io.BytesIO()
                        with pd.ExcelWriter(buffer_original, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 Download Original Excel",
                            data=buffer_original.getvalue(),
                            file_name="original_data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_original"
                        )
            
            except Exception as e:
                st.error(f"Error saving changes: {str(e)}")
        
        return edited_df
        
    except Exception as e:
        st.error(f"Error displaying extracted data: {str(e)}")
        return df


def modify_history_tab():
    st.markdown("### 📂 Previous Uploads")
    user_uploads = get_user_uploads(st.session_state.username)
    
    if not user_uploads.empty:
        for idx, row in user_uploads.iterrows():
            session_id = f"session_{idx}"
            
            with st.expander(f"Upload from {row['Upload Date']}"):
                view_tab, download_tab, share_tab = st.tabs(["View Files", "Download Files", "Share Files"])
                
                with view_tab:
                    st.markdown("**📄 View Invoice PDFs:**")
                    for pdf_idx, pdf_name in enumerate(row['Invoice Files'].split(', ')):
                        pdf_path = os.path.join(row['Path'], pdf_name)
                        if os.path.exists(pdf_path):
                            if st.button(f"View {pdf_name}", key=f"view_pdf_{session_id}_{pdf_idx}"):
                                with open(pdf_path, 'rb') as pdf_file:
                                    pdf_data = pdf_file.read()
                                    display_pdf(pdf_data)
                    
                    st.markdown("**📊 View Excel Result:**")
                    excel_path = os.path.join(row['Path'], row['Excel Result'])
                    if os.path.exists(excel_path):
                        if st.button(f"View {row['Excel Result']}", key=f"view_excel_{session_id}"):
                            with open(excel_path, 'rb') as excel_file:
                                excel_data = excel_file.read()
                                display_excel_native(excel_data)
                
                with download_tab:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📄 Download Invoice PDFs:**")
                        for pdf_idx, pdf_name in enumerate(row['Invoice Files'].split(', ')):
                            pdf_path = os.path.join(row['Path'], pdf_name)
                            if os.path.exists(pdf_path):
                                st.download_button(
                                    f"📥 {pdf_name}",
                                    download_stored_file(pdf_path),
                                    file_name=pdf_name,
                                    mime="application/pdf",
                                    key=f"download_pdf_{session_id}_{pdf_idx}"
                                )
                    
                    with col2:
                        st.markdown("**📊 Download Excel Result:**")
                        excel_path = os.path.join(row['Path'], row['Excel Result'])
                        if os.path.exists(excel_path):
                            st.download_button(
                                f"📥 {row['Excel Result']}",
                                download_stored_file(excel_path),
                                file_name=row['Excel Result'],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"download_excel_{session_id}"
                            )
                
                with share_tab:
                    st.markdown("**🔗 Share Files:**")
                    if st.button("Generate Links", key=f"share_{session_id}"):
                        share_links = []
                        
                        for pdf_name in row['Invoice Files'].split(', '):
                            pdf_path = os.path.join(row['Path'], pdf_name)
                            if os.path.exists(pdf_path):
                                pdf_link = generate_share_link(pdf_path)
                                if pdf_link:
                                    share_links.append((pdf_name, pdf_link))
                        
                        excel_path = os.path.join(row['Path'], row['Excel Result'])
                        if os.path.exists(excel_path):
                            excel_link = generate_share_link(excel_path)
                            if excel_link:
                                share_links.append((row['Excel Result'], excel_link))
                        
                        if share_links:
                            st.markdown("**Generated Links:**")
                            for link_idx, (file_name, link) in enumerate(share_links):
                                with st.container():
                                    st.text(file_name)
                                    st.code(link)
                                    if st.button(
                                        "📋 Copy Link",
                                        key=f"copy_{session_id}_{link_idx}"
                                    ):
                                        st.write(f"```{link}```")
                                    st.markdown("---")
    else:
        st.info("No previous uploads found")

    """Display Excel data using native Streamlit components"""
    try:
        df = pd.read_excel(io.BytesIO(excel_data))
        
        excel_file = io.BytesIO(excel_data)
        xl = pd.ExcelFile(excel_file)
        sheet_names = xl.sheet_names
        
        if len(sheet_names) > 1:
            selected_sheet = st.selectbox("Select Sheet:", sheet_names)
            df = pd.read_excel(excel_file, sheet_name=selected_sheet)

        search = st.text_input("🔍 Search in table:", key="excel_search")
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df = df[mask]
        
        st.dataframe(
            df,
            use_container_width=True,
            height=600,
            hide_index=True
        )
        
        st.download_button(
            "📥 Download Excel File",
            excel_data,
            file_name="downloaded_file.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        return df
    except Exception as e:
        st.error(f"Error displaying Excel file: {str(e)}")
        return None

def display_pdf(pdf_data):
    """Display PDF as images while maintaining PDF download capability"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
            tmp_pdf.write(pdf_data)
            pdf_path = tmp_pdf.name


        st.download_button(
            label="📥 Download PDF",
            data=pdf_data,
            file_name="document.pdf",
            mime="application/pdf"
        )

        os.unlink(pdf_path)
        
    except Exception as e:
        st.error(f"Error displaying PDF: {str(e)}")
        st.download_button(
            label="⚠️ Download PDF",
            data=pdf_data,
            file_name="document.pdf",
            mime="application/pdf"
        )

def generate_share_link(file_path, expiry_days=7):
    """Generate a shareable link for a file"""
    try:
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
        
        share_info = {
            'file_path': file_path,
            'expiry_date': expiry_date,
            'original_filename': os.path.basename(file_path)
        }
        
        shares_dir = 'storage/shares'
        os.makedirs(shares_dir, exist_ok=True)
        
        share_file = os.path.join(shares_dir, f'{file_hash}.json')
        with open(share_file, 'w') as f:
            json.dump(share_info, f)
            
        base_url = "https://aki-asn.streamlit.app"
        
        share_link = f"{base_url}/?share={file_hash}"
        
        return share_link
        
    except Exception as e:
        st.error(f"Error generating share link: {str(e)}")
        return None

def auto_download_shared_file():
    """Automatically handle file download based on URL parameters"""
    try:
        current_path = st.query_params.get('path', '')
        
        if current_path.startswith('download/'):
            file_hash = current_path.split('/')[-1]
            share_file = f'storage/shares/{file_hash}.json'
            
            if not os.path.exists(share_file):
                st.error("This download link is invalid or has expired.")
                return
            
            with open(share_file, 'r') as f:
                share_info = json.load(f)
            
            expiry_date = datetime.strptime(share_info['expiry_date'], '%Y-%m-%d')
            if datetime.now() > expiry_date:
                os.remove(share_file)
                st.error("This download link has expired.")
                return
            
            file_path = share_info['file_path']
            if not os.path.exists(file_path):
                st.error("The file is no longer available.")
                return
            
            file_data = download_stored_file(file_path)
            if file_data:
                original_filename = share_info['original_filename']
                mime_type = ("application/pdf" if original_filename.lower().endswith('.pdf') 
                           else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                st.markdown("""
                    <style>
                        .stDownloadButton button {
                            width: 100%;
                            height: 60px;
                            font-size: 20px;
                            margin-top: 20px;
                        }
                        .centered {
                            text-align: center;
                            padding: 20px;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                st.markdown(f"<div class='centered'><h2>📥 Downloading {original_filename}</h2></div>", 
                          unsafe_allow_html=True)
                
                components.html(
                    f"""
                    <html>
                        <body>
                            <script>
                                window.onload = function() {{
                                    setTimeout(function() {{
                                        document.getElementById('download-button').click();
                                    }}, 500);
                                }}
                            </script>
                        </body>
                    </html>
                    """,
                    height=0,
                )
                
                st.download_button(
                    label=f"Download {original_filename}",
                    data=file_data,
                    file_name=original_filename,
                    mime=mime_type,
                    key="download-button"
                )
                
                st.markdown("<div class='centered'><p>If the download doesn't start automatically, click the button above.</p></div>", 
                          unsafe_allow_html=True)
                
            else:
                st.error("Unable to prepare the file for download.")
            
    except Exception as e:
        st.error(f"Error processing download: {str(e)}")
    
def handle_download_page(share_hash):
    try:
        share_info = get_shared_file(share_hash)
        if not share_info:
            st.error("Invalid or expired download link")
            return

        file_path = share_info['file_path']
        if not os.path.exists(file_path):
            st.error("File no longer exists")
            return

        file_data = download_stored_file(file_path)
        if not file_data:
            return

        original_filename = share_info['original_filename']
        
        if original_filename.lower().endswith('.pdf'):
            base64_pdf = base64.b64encode(file_data).decode('utf-8')
            pdf_display = f'''
                <embed src="data:application/pdf;base64,{base64_pdf}" 
                       type="application/pdf" 
                       width="100%" 
                       height="800px" 
                       internalinstanceid="pdf-display">
            '''
            st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            try:
                df = pd.read_excel(io.BytesIO(file_data))
                st.markdown(f"### 📊 {original_filename}")
                search = st.text_input("🔍 Search in table:", "")
                if search:
                    mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                    filtered_df = df[mask]
                else:
                    filtered_df = df
                
                st.markdown(f"**Total Rows:** {len(filtered_df)} | **Total Columns:** {len(filtered_df.columns)}")
                
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    height=600
                )
                
                st.download_button(
                    "📥 Download Excel File",
                    file_data,
                    file_name=original_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Error displaying Excel file: {str(e)}")
                # Fallback to download button if display fails
                st.download_button(
                    label="Download File",
                    data=file_data,
                    file_name=original_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Error handling download: {str(e)}")
        st.error(traceback.format_exc())

def verify_storage_setup():
    """Verify that storage is set up correctly"""
    try:
        if not os.path.exists('storage'):
            return False
            
        shares_dir = 'storage/shares'
        if not os.path.exists(shares_dir):
            return False
                
        return True
    except Exception as e:
        st.error(f"Error verifying storage: {str(e)}")
        return False

def setup_storage():
    """Create necessary directories for file storage"""
    if not os.path.exists('storage'):
        os.makedirs('storage')
    
    if not os.path.exists('storage/uploads_tracking.xlsx'):
        df = pd.DataFrame(columns=['Username', 'Upload Date', 'Invoice Files', 'Excel Result', 'Path'])
        df.to_excel('storage/uploads_tracking.xlsx', index=False)



def save_uploaded_files(username, pdf_files, excel_data):
    """Save uploaded PDFs and Excel result"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_dir = username.split('@')[0]
        save_path = f'storage/{user_dir}/{timestamp}'
        os.makedirs(save_path, exist_ok=True)
        
        pdf_names = []
        for pdf in pdf_files:
            pdf_path = f'{save_path}/{pdf.name}'
            with open(pdf_path, 'wb') as f:
                f.write(pdf.getvalue())
            pdf_names.append(pdf.name)
        
        excel_name = f'ASN_Result_{timestamp}.xlsx'
        excel_path = f'{save_path}/{excel_name}'
        excel_data.to_excel(excel_path, index=False)
        
        tracking_df = pd.read_excel('storage/uploads_tracking.xlsx')
        new_row = {
            'Username': username,
            'Upload Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Invoice Files': ', '.join(pdf_names),
            'Excel Result': excel_name,
            'Path': save_path
        }
        tracking_df = pd.concat([tracking_df, pd.DataFrame([new_row])], ignore_index=True)
        tracking_df.to_excel('storage/uploads_tracking.xlsx', index=False)
        
        return save_path
        
    except Exception as e:
        st.error(f"Error saving files: {str(e)}")
        return None

def get_user_uploads(username):
    """Get all previous uploads for a user"""
    try:
        tracking_df = pd.read_excel('storage/uploads_tracking.xlsx')
        user_uploads = tracking_df[tracking_df['Username'] == username].copy()
        return user_uploads.sort_values('Upload Date', ascending=False)
    except Exception as e:
        st.error(f"Error retrieving uploads: {str(e)}")
        return pd.DataFrame()

def download_stored_file(file_path):
    """Read a stored file for downloading"""
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None
def init_ocr():
    """Initialize OCR with optimized settings"""
    """
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(
            use_angle_cls=False,
            lang='en',
            use_gpu=False,
            show_log=False
        )
        return ocr
    except Exception as e:
        st.error(f"Error initializing OCR: {str(e)}")
        return None
    """
    return None



st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            margin-top: 20px;
        }
        .main {
            padding: 2rem;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 30px;
        }
        .stAlert {
            padding: 20px;
            margin: 10px 0;
        }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

if 'username' not in st.session_state or not st.session_state.username:
    st.session_state.username = 'Institution@akigroup.com'

DEFAULT_PASSWORD = 'AKI@2025'
USER_TRACKING_FILE = 'user_tracking.xlsx'
  
def validate_email(email): 
    return (email.lower().endswith('consumer.dept@akigroup.com') or 
            email.lower().endswith('pharma.dept@akigroup.com') or
            email.lower().endswith('medlab.dept@akigroup.com') or
            email.lower().endswith('admin@akigroup.com') or
            email.lower().endswith('mhd'))

def get_shared_file(share_hash):
    """Retrieve shared file information"""
    try:
        share_file = f'storage/shares/{share_hash}.json'
        if not os.path.exists(share_file):
            return None
            
        with open(share_file, 'r') as f:
            share_info = json.load(f)
            
        expiry_date = datetime.strptime(share_info['expiry_date'], '%Y-%m-%d')
        if datetime.now() > expiry_date:
            os.remove(share_file)  
            return None
            
        return share_info
    
    except Exception as e:
        st.error(f"Error retrieving shared file: {str(e)}")
        return None

def init_user_tracking():
    return
            

def display_history_tab():
    st.markdown("### 📂 Previous Uploads")
    user_uploads = get_user_uploads(st.session_state.username)
    
    if not user_uploads.empty:
        for idx, row in user_uploads.iterrows():
            session_id = f"session_{idx}"
            
            with st.expander(f"Upload from {row['Upload Date']}"):
                st.write(f"**Invoice Files:** {row['Invoice Files']}")
                
                pdf_col, excel_col, share_col = st.columns(3)
                
                with pdf_col:
                    st.markdown("**📄 Invoice PDFs:**")
                    for pdf_idx, pdf_name in enumerate(row['Invoice Files'].split(', ')):
                        pdf_path = os.path.join(row['Path'], pdf_name)
                        if os.path.exists(pdf_path):
                            pdf_key = f"pdf_{session_id}_{pdf_idx}_{hash(pdf_name)}"
                            st.download_button(
                                f"📥 {pdf_name}",
                                download_stored_file(pdf_path),
                                file_name=pdf_name,
                                mime="application/pdf",
                                key=pdf_key
                            )
                
                with excel_col:
                    st.markdown("**📊 Excel Result:**")
                    excel_path = os.path.join(row['Path'], row['Excel Result'])
                    if os.path.exists(excel_path):
                        excel_key = f"excel_{session_id}_{hash(row['Excel Result'])}"
                        st.download_button(
                            f"📥 {row['Excel Result']}",
                            download_stored_file(excel_path),
                            file_name=row['Excel Result'],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=excel_key
                        )
                
                with share_col:
                    st.markdown("**🔗 Share Files:**")
                    share_key = f"share_{session_id}"
                    if st.button("Generate Links", key=share_key):
                        share_links = []
                
                        for pdf_name in row['Invoice Files'].split(', '):
                            pdf_path = os.path.join(row['Path'], pdf_name)
                            if os.path.exists(pdf_path):
                                pdf_link = generate_share_link(pdf_path)
                                if pdf_link:
                                    share_links.append((pdf_name, pdf_link))
                        
                        excel_path = os.path.join(row['Path'], row['Excel Result'])
                        if os.path.exists(excel_path):
                            excel_link = generate_share_link(excel_path)
                            if excel_link:
                                share_links.append((row['Excel Result'], excel_link))
                        
                        if share_links:
                            st.markdown("**Generated Links:**")
                            for link_idx, (file_name, link) in enumerate(share_links):
                                link_container_key = f"link_container_{session_id}_{link_idx}"
                                with st.container(key=link_container_key):
                                    st.text(file_name)
                                    st.code(link)
                
                                    copy_key = f"copy_{session_id}_{link_idx}"
                                    st.button(
                                        "📋 Copy Link",
                                        key=copy_key,
                                        on_click=lambda l=link: st.write(f"```{l}```")
                                    )
                                    st.markdown("---")
    else:
        st.info("No previous uploads found")

def update_user_tracking(username, files_uploaded=0, rows_processed=0, pages_processed=0):
    return


def is_scanned_pdf(pdf_path):
    """Check if PDF is scanned by attempting to extract text"""
    try:
        with fitz.open(pdf_path) as pdf:
            text_content = ""
            for page in pdf:
                text_content += page.get_text() or ""

            if len(text_content.strip()) < 100:
                st.info("We are working on it now") 
                return True
            return False
    except Exception as e:
        st.error(f"Error checking PDF type: {str(e)}")
        return True



def process_invoice_lines(invoice_info):
    """
    Process invoice information lines with standardized headers
    """
    try:
        header_mappings = {
            'Customer Number': 'Customer No',
            'Customer No.': 'Customer No',
            'Supplier Name': 'Supplier',
            'Total VAT': 'VAT',
            'Total VAT or VAT': 'VAT',
            'Total Amount of the Invoice': 'Invoice Total',
            'Payer Name': 'Payer Name',
            'Date of Invoice': 'Invoice Date',
            'Manufacturing Date': 'Mfg Date',
            'Manufacture Date': 'Mfg Date',
            'Production Date': 'Mfg Date',
            'Prod Date': 'Mfg Date',
            'Prod. Date': 'Mfg Date',
            'Date of Manufacture': 'Mfg Date',
            'DOM': 'Mfg Date',
            'Manufactured On': 'Mfg Date',
            'Manuf. Date': 'Mfg Date'
        }
        
        standard_headers = [
            'PO Number', 'Item Code', 'Description', 'UOM', 'Quantity',
            'Lot Number', 'Expiry Date', 'Mfg Date', 'Invoice No',
            'Unit Price', 'Total Price', 'Country', 'HS Code',
            'Invoice Date', 'Customer No', 'Payer Name', 'Currency',
            'Supplier', 'Invoice Total', 'VAT'
        ]

        lines = [line.strip() for line in invoice_info.split('\n')]
        valid_lines = []
        
        for line in lines:
            if not line:
                continue
            if '--' in line and '|' not in line:
                valid_lines.append(line)
                continue
            if set(line).issubset({'-', ' '}):
                continue
            if '|' in line:
                cleaned_cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                valid_lines.append('|'.join(cleaned_cells))

        headers = None
        data_rows = []
        raw_headers = None
        
        for line in valid_lines:
            if '--' in line and '|' not in line:
                continue
                
            if '|' in line:
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                
                if headers is None:
                    raw_headers = cells
                    headers = standard_headers
                    # st.write(f"DEBUG - Original headers: {raw_headers}")
                    # st.write(f"DEBUG - Standardized headers: {headers}")
                else:
                    data_dict = {}
                    for i, cell in enumerate(cells):
                        if i < len(raw_headers):
                            data_dict[raw_headers[i]] = cell

                    standardized_row = []
                    for header in headers:
                        value = ''
                        mapped_found = False
                        for raw_key, std_key in header_mappings.items():
                            if std_key == header and raw_key in data_dict:
                                value = data_dict[raw_key]
                                mapped_found = True
                                break
                        
                        if not mapped_found and header in data_dict:
                            value = data_dict[header]
                        
                        standardized_row.append(value)
                    data_rows.append(standardized_row)

        if headers and data_rows:
            for i, row in enumerate(data_rows):
                if len(row) != len(headers):
                    # st.write(f"DEBUG - Row {i} length mismatch: {len(row)} vs {len(headers)}")
                    # st.write(f"DEBUG - Row data: {row}")
                    # Pad or trim row to match header length
                    if len(row) < len(headers):
                        row.extend([''] * (len(headers) - len(row)))
                    else:
                        data_rows[i] = row[:len(headers)]

        return headers, data_rows
        
    except Exception as e:
        st.error(f"Error in process_invoice_lines: {str(e)}")
        st.error(traceback.format_exc())
        return None, None



def count_processed_rows(invoice_info):
    """
    Count actual data rows, excluding separators and headers
    """
    try:
        lines = [line.strip() for line in invoice_info.split('\n')]
        
        data_rows = 0
        header_found = False
        
        for line in lines:
            if not line or set(line.replace('|', '')).issubset({'-', ' '}):
                continue
                
            if not header_found:
                header_found = True
                continue
                
            data_rows += 1
            
        return data_rows
        
    except Exception as e:
        st.error(f"Error counting processed rows: {str(e)}")
        return 0



def extract_text_from_scanned_pdf(pdf_path):
    """Extract text from scanned PDF using OCR methods"""
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # First try with doctr
                try:
                    doc = DocumentFile.from_pdf(pdf_path)
                    doctr_model = ocr_predictor(det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True)
                    result = doctr_model(doc)
                    
                    # Extract text from doctr result
                    extracted_text = []
                    for page in result.pages:
                        for block in page.blocks:
                            for line in block.lines:
                                for word in line.words:
                                    extracted_text.append(word.value)
                    
                    if extracted_text:
                        st.success("Successfully extracted text using doctr")
                        return " ".join(extracted_text)
                    
                except Exception as doctr_error:
                    st.warning(f"Doctr extraction failed, falling back to PaddleOCR: {str(doctr_error)}")
                
                # Initialize PaddleOCR with English language and no angle classification
                ocr = PaddleOCR(use_angle_cls=False, lang='en')
                
                # Open PDF with PyMuPDF
                pdf_document = fitz.open(pdf_path)
                all_results = []
                total_pages = len(pdf_document)
                
                # Process each page with progress bar
                progress_bar = st.progress(0)
                
                for page_num in range(total_pages):
                    try:
                        # Get page and convert to image
                        page = pdf_document[page_num]
                        pix = page.get_pixmap(alpha=False)
                        
                        # Convert to numpy array
                        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                            pix.height, pix.width, 3 if pix.n >= 3 else 1
                        )
                        
                        if img_array.shape[-1] == 1:
                            img_array = np.repeat(img_array, 3, axis=-1)
                        
                        # Run OCR
                        result = ocr.ocr(img_array, cls=False)
                        
                        if result:
                            page_text = []
                            for line in result:
                                if isinstance(line, (list, tuple)):
                                    for item in line:
                                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                                            text = item[1][0] if isinstance(item[1], (list, tuple)) else item[1]
                                            page_text.append(str(text))
                            
                            all_results.extend(page_text)
                    
                    except Exception as ocr_error:
                        st.warning(f"Error in OCR processing for page {page_num + 1}: {str(ocr_error)}")
                        continue
                    
                    progress_bar.progress((page_num + 1) / total_pages)
                    gc.collect()
                
                pdf_document.close()
                progress_bar.empty()
                
                if all_results:
                    return "\n".join(all_results)
                else:
                    st.error("No text was extracted from the PDF")
                    return None
                    
            except Exception as e:
                st.error(f"PDF processing error: {str(e)}")
                return None
            
    except Exception as e:
        st.error(f"OCR processing error: {str(e)}")
        return None
    """
    st.info("We are working on it now")
    return None


def check_shared_file():
    """Handle shared file viewing and downloading"""
    try:
        share_hash = st.query_params.get('share')
        
        if share_hash:
            share_info = get_shared_file(share_hash)
            if share_info:
                file_path = share_info['file_path']
                if os.path.exists(file_path):
                    file_data = download_stored_file(file_path)
                    if file_data:
                        file_name = os.path.basename(file_path)
                        st.markdown(f"### 📄 File: {file_name}")
                        
                        if file_name.lower().endswith('.pdf'):
                            st.info("Loading PDF viewer... If the viewer doesn't load, you can use the download options.")
                            display_pdf(file_data)
                        else:
                            try:
                                df = pd.read_excel(io.BytesIO(file_data))
                                
                                search = st.text_input("🔍 Search in table:", key="excel_search")
                                if search:
                                    mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                                    df = df[mask]
                                st.markdown(f"**Total Rows:** {len(df)} | **Total Columns:** {len(df.columns)}")
                                
                                st.dataframe(
                                    df,
                                    use_container_width=True,
                                    height=600
                                )
                                st.download_button(
                                    "📥 Download Excel File",
                                    file_data,
                                    file_name=file_name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            except Exception as excel_error:
                                st.error(f"Error displaying Excel file: {str(excel_error)}")
                                st.download_button(
                                    label="Download File",
                                    data=file_data,
                                    file_name=file_name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                    else:
                        st.error("Unable to read the shared file.")
                else:
                    st.error("The shared file no longer exists.")
            else:
                st.error("This share link has expired or is invalid.")
    except Exception as e:
        st.error(f"Error processing shared file: {str(e)}")
        st.error(traceback.format_exc())



def login_page():
    pass


def extract_text_pdf(pdf_path):
    """Extract text from PDF, handling both scanned and machine-readable PDFs"""
    if is_scanned_pdf(pdf_path):
        st.info("We are working on scanned PDFs. Please wait...")
        return None
    else:
        try:
            with fitz.open(pdf_path) as pdf:
                unique_pages = {}
                for page_num, page in enumerate(pdf):
                    page_text = page.get_text()
                    content_hash = hash(page_text)
                    if content_hash not in unique_pages:
                        unique_pages[content_hash] = page_text
                return "\n".join(unique_pages.values())
        except Exception as e:
            st.error(f"Error extracting text: {str(e)}")
            return None
            

def format_markdown_table(headers, data):
    """
    Create a properly formatted Markdown table with consistent separator line
    """
    table = [f"| {' | '.join(headers)} |"]
    
    separator = [f"|{'|'.join('-' * (len(header) + 2) for header in headers)}|"]
    
    data_rows = [f"| {' | '.join(row)} |" for row in data]
    
    return '\n'.join(table + separator + data_rows)

def split_table_by_rows(table_text, max_rows=50):
    return [table_text]


def using_groq(text: str):
    """
    Process invoice text through OpenAI API with a single, strong prompt.
    Returns a clean pipe-delimited table including all line items.
    """
    if not text:
        return None

    prompt = f"""
You are an expert invoice extractor. Return ONLY a pipe-delimited table that contains EVERY line item.

Document text:
{text}

Rules:
- Do not skip any items. If line items span multiple pages or are split by headers/footers, merge logically and include them.
- If multiple batches/lots/expiries exist for the same product, create a separate row per batch-expiry combination.
- If a required field is missing, infer carefully from context; otherwise use "-" (never leave blank).
- Item codes must be valid product codes (>= 6 digits). Ignore row/line numbers like 300, 310, etc.
- Normalize country codes to full country names where possible.
- Dates should be dd-MMM-yy when present.
- Currency: infer from supplier location if needed (EUR for Europe, USD for USA, THB for Thailand) when not explicit.
- Payer Name must be exactly: ALPHAMED GENERAL TRADING LLC.

Output format:
- Return ONLY a Markdown table with these exact columns in order:
  | PO Number | Item Code | Description | UOM | Quantity | Lot Number | Expiry Date | Mfg Date | Invoice No | Unit Price | Total Price | Country | HS Code | Invoice Date | Customer No | Payer Name | Currency | Supplier | Invoice Total | VAT |
- Include the separator line and one row per item/batch.
"""

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract invoice line items with perfect recall and precision. "
                        "Always return a complete pipe-delimited table with the required columns only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error in API call: {str(e)}")
        return None


# def using_groq(text: str):
#     """
#     Process invoice text through OpenAI API with enhanced focus on batch extraction,
#     with special handling for large files.
    
#     Args:
#         text (str): The text extracted from the invoice PDF
        
#     Returns:
#         str: The processed invoice information with structured data
#     """
#     import re
    
#     if not text:
#         return None
    
#     estimated_tokens = len(text) // 4
    
#     # Pre-process the text to identify products with multiple batches
#     # This helps us ensure we don't lose batch information when chunking
#     product_batches = {}
    
#     # Look for batch patterns
#     batch_patterns = [
#         r'(?i)Batch\s*No\s*:\s*([A-Z0-9]+).*?Quantity\s*:\s*(\d+)',
#         r'(?i)Batch\s*No\s*:\s*([A-Z0-9]+)',
#         r'(?i)Lot\s*Number\s*:\s*([A-Z0-9]+)',
#         r'(?i)Batch/Lot\s*:\s*([A-Z0-9]+)'
#     ]
    
#     # Try to find product codes associated with batches
#     product_code_pattern = r'(?i)(?:Supplier\s*Item\s*Code|Item\s*Code)\s*:?\s*([0-9]{10,14})'
    
#     # Find product descriptions
#     product_desc_pattern = r'(?i)(?:Supplier\s*Description|Description)\s*:?\s*([A-Za-z0-9\s]+)'
    
#     # Look for multiple batches in the text before chunking
#     current_product = None
#     current_description = None
    
#     lines = text.split('\n')
#     for i, line in enumerate(lines):
#         # Try to identify product code
#         product_match = re.search(product_code_pattern, line)
#         if product_match:
#             current_product = product_match.group(1)
            
#             # Try to find description in the same line or next line
#             desc_match = re.search(product_desc_pattern, line)
#             if desc_match:
#                 current_description = desc_match.group(1).strip()
#             elif i+1 < len(lines):
#                 desc_match = re.search(product_desc_pattern, lines[i+1])
#                 if desc_match:
#                     current_description = desc_match.group(1).strip()
        
#         # If we have a current product, look for batch information
#         if current_product:
#             for pattern in batch_patterns:
#                 batch_matches = re.finditer(pattern, line)
#                 for match in batch_matches:
#                     batch_number = match.group(1)
                    
#                     # Look for quantity, manufacturing date, and expiry date near this batch
#                     quantity = None
#                     mfg_date = None
#                     exp_date = None
                    
#                     # Check current line and next few lines for associated info
#                     context_lines = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                    
#                     # Extract quantity
#                     qty_match = re.search(rf'(?i)(?:Quantity|Qty).*?{batch_number}.*?:\s*(\d+)', context_lines)
#                     if not qty_match:
#                         qty_match = re.search(r'(?i)(?:Quantity|Qty)\s*:\s*(\d+)', context_lines)
#                     if qty_match:
#                         quantity = qty_match.group(1)
                    
#                     # Extract manufacturing date
#                     mfg_match = re.search(rf'(?i)(?:Manuf\.?|Manufacturing)\s*Date.*?{batch_number}.*?:\s*([0-9\-]+)', context_lines)
#                     if not mfg_match:
#                         mfg_match = re.search(r'(?i)(?:Manuf\.?|Manufacturing)\s*Date\s*:\s*([0-9\-]+)', context_lines)
#                     if mfg_match:
#                         mfg_date = mfg_match.group(1)
                    
#                     # Extract expiry date
#                     exp_match = re.search(rf'(?i)(?:Expiry|Exp\.?)\s*Date.*?{batch_number}.*?:\s*([0-9\-]+)', context_lines)
#                     if not exp_match:
#                         exp_match = re.search(r'(?i)(?:Expiry|Exp\.?)\s*Date\s*:\s*([0-9\-]+)', context_lines)
#                     if exp_match:
#                         exp_date = exp_match.group(1)
                    
#                     # Store all the batch information
#                     if current_product not in product_batches:
#                         product_batches[current_product] = {
#                             'description': current_description,
#                             'batches': []
#                         }
                    
#                     product_batches[current_product]['batches'].append({
#                         'batch_number': batch_number,
#                         'quantity': quantity,
#                         'mfg_date': mfg_date,
#                         'exp_date': exp_date
#                     })
    
#     # Enhanced prompt with MUCH stronger emphasis on multiple batches
#     prompt_template = """Extract ALL invoice line items without skipping ANY. Every line must have ALL fields filled.

# {text_content}

# ### CRITICAL INSTRUCTION: CREATE SEPARATE ROWS FOR EACH BATCH
# When a product has multiple batches, you MUST create a separate row for EACH batch.
# For example, if PARODONTAX COMPLETE PRO TB SOFT 1X1 has 3 batches (4316158, 5028371, 5029171), 
# create THREE SEPARATE ROWS with the same item code and description but different batch numbers,
# quantities, manufacturing dates, and expiry dates.

# {known_batches_info}

# ### Mandatory Fields (Every row must have values):
#    - PO Number: Order Number or Purchase Order fields. 
#      IMPORTANT: Remove any text like "MDS", "-MDS", "/MDS" after the number
#      If not found, use "-"
#    - Item Code: MUST be the full product code, usually 12-15 digits (e.g., 60000000128537)
#      If you see shorter numeric codes like "300" or "310", look for the actual full item code
#      NEVER use short numbers like 300, 310, etc. as item codes - these are likely line numbers
#    - Description: If missing, use "Product Line " + line number
#    - UOM: Unit of Measure 
#    - Quantity: or Quantity Shipped - IMPORTANT: Each batch has its own quantity
#    - Lot Number: Example: "Batch/serial Nr 272130" means lot number is "272130"
#                  *** CRITICAL: When you see "Batch No: 4316158, 5028371, 5029171" or multiple batches anywhere, 
#                  you MUST create SEPARATE ROWS for each batch number ***
#                  Only use "N/A" if confirmed missing after thorough search
#    - Expiry Date: use "-" if missing, format as DD-MMM-YY
#                   *** CRITICAL: Each batch usually has its own expiry date - create separate rows accordingly ***
#    - Manufacturing Date or Mfg Date: Each batch usually has its own manufacturing date
#    - Invoice No: MUST be found - look in header
#    - Unit Price: Default to Total Price if missing
#    - Total Price: Default to Unit Price × Quantity if missing
#    - Country: Convert codes to full names (e.g., IE → Ireland)
#    - HS Code: Default "-" if missing
#    - Invoice Date: Extract from header or near invoice number (format: dd-MMM-yy)
#    - Customer No: Extract from "Customer Nr" fields or fallback to company code
#    - Payer Name: ALWAYS exactly "ALPHAMED GENERAL TRADING LLC." (no exceptions)
#    - Currency: Use "EUR" for European suppliers, "USD" for USA, "THB" for Thailand
#    - Supplier: MUST find the company name from letterhead/invoice header
#    - Invoice Total: Sum all line totals if not explicitly stated
#    - VAT: Look for VAT percentage or amount - use "0" if not found

# DO NOT SKIP ANY LINE ITEMS. If you see item codes or sequential line items even without full details, include them all.
# If you see a table with entries in the document, extract EVERY LINE in that table regardless of context.

# THIS IS CRUCIAL: If a product appears only once but has multiple batches listed together (e.g., "Batch No: 4316158, 5028371, 5029171"), 
# you MUST create SEPARATE ROWS for each batch. NEVER combine multiple batches in a single row.

# ### Output Format:
# Return ONLY a clean table with pipe delimiters (|) between columns. Include a header row and separator line.
# Each data row should represent ONE line item or ONE batch from the invoice.

# {chunk_directive}
# """
    
#     # Prepare known batches info string
#     known_batches_info = ""
#     if product_batches:
#         known_batches_info = "### KNOWN PRODUCTS WITH MULTIPLE BATCHES (ENSURE THESE ARE EXTRACTED CORRECTLY):\n"
#         for product_code, info in product_batches.items():
#             batches_str = ", ".join([b['batch_number'] for b in info['batches']])
#             known_batches_info += f"- Product {product_code} ({info['description'] or 'Unknown Description'}) has these batches: {batches_str}\n"
#             known_batches_info += "  YOU MUST create separate rows for each of these batches.\n"
    
#     if estimated_tokens < 7000:
#         prompt = prompt_template.format(
#             text_content=text,
#             known_batches_info=known_batches_info,
#             chunk_directive=""
#         )
        
#         try:
#             from openai import OpenAI
#             client = OpenAI(api_key=open_api_key)
            
#             completion = client.chat.completions.create(
#                 model="gpt-4o",  
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": "You are an invoice processing assistant focused on accurate extraction. Your TOP PRIORITY is to create separate rows for each batch when multiple batches exist for the same item. NEVER combine multiple batches into a single row."
#                     },
#                     {
#                         "role": "user",
#                         "content": prompt
#                     }
#                 ],
#                 temperature=0.1
#             )
#             return completion.choices[0].message.content
#         except Exception as e:
#             st.error(f"Error in API call: {str(e)}")
#             return None
            
#     # Handle large documents with improved chunking
#     st.info(f"Processing large document (est. {estimated_tokens} tokens) using improved multi-batch chunking...")
    
#     # Improved chunking strategy that preserves batch information
#     from collections import defaultdict
    
#     # First, identify complete sections for products
#     product_sections = defaultdict(list)
#     current_section = []
#     current_section_product = None
    
#     # Enhanced parsing to identify product sections
#     lines = text.split('\n')
#     i = 0
#     while i < len(lines):
#         line = lines[i]
        
#         # Check if line contains a product code
#         product_match = re.search(product_code_pattern, line)
        
#         # If we found a new product code, start a new section
#         if product_match:
#             # If we had a previous section, save it
#             if current_section and current_section_product:
#                 product_sections[current_section_product].extend(current_section)
            
#             # Start new section
#             current_section_product = product_match.group(1)
#             current_section = [line]
            
#             # Include surrounding lines for context
#             start_idx = max(0, i-5)
#             end_idx = min(len(lines), i+20)  # Include more lines after product code for batch info
            
#             # Add context before the product code line
#             for j in range(start_idx, i):
#                 current_section.insert(0, lines[j])
            
#             # Continue reading lines until we either find another product or reach max lines
#             context_lines_added = 0
#             j = i + 1
#             while j < end_idx and context_lines_added < 20:
#                 next_line = lines[j]
#                 # Stop if we find another product code
#                 if re.search(product_code_pattern, next_line):
#                     break
#                 current_section.append(next_line)
#                 context_lines_added += 1
#                 j += 1
            
#             # Skip the lines we've already added
#             i = j
#         else:
#             # Just move to next line
#             i += 1
    
#     # Add the last section
#     if current_section and current_section_product:
#         product_sections[current_section_product].extend(current_section)
    
#     # Now we process each product individually or in logical chunks
#     all_results = []
#     progress_bar = st.progress(0)
    
#     # First, process known products with multiple batches
#     total_products = len(product_sections) + 1  # +1 for the rest of the text
#     product_idx = 0
    
#     for product_code, product_text in product_sections.items():
#         if product_code in product_batches:
#             status_text = st.empty()
#             status_text.text(f"Processing product {product_code} with multiple batches...")
            
#             # Create a focused chunk for this product
#             product_chunk = "\n".join(product_text)
            
#             # Create a specific prompt for this product
#             specific_known_batches = f"### THIS PRODUCT HAS MULTIPLE BATCHES:\n"
#             specific_known_batches += f"- Product {product_code} ({product_batches[product_code]['description'] or 'Unknown Description'}) has these batches:\n"
#             for batch in product_batches[product_code]['batches']:
#                 batch_info = f"  - Batch: {batch['batch_number']}"
#                 if batch['quantity']:
#                     batch_info += f", Quantity: {batch['quantity']}"
#                 if batch['mfg_date']:
#                     batch_info += f", Mfg Date: {batch['mfg_date']}"
#                 if batch['exp_date']:
#                     batch_info += f", Exp Date: {batch['exp_date']}"
#                 specific_known_batches += batch_info + "\n"
#             specific_known_batches += "CREATE SEPARATE ROWS for each batch above.\n"
            
#             prompt = prompt_template.format(
#                 text_content=product_chunk,
#                 known_batches_info=specific_known_batches,
#                 chunk_directive=f"\nThis chunk contains product {product_code} which has multiple batches. Extract each batch as a separate row."
#             )
            
#             try:
#                 from openai import OpenAI
#                 client = OpenAI(api_key=open_api_key)
                
#                 completion = client.chat.completions.create(
#                     model="gpt-4o",
#                     messages=[
#                         {
#                             "role": "system",
#                             "content": f"You are an invoice processing assistant. Your ONLY task is to extract product {product_code} with its multiple batches. Create a SEPARATE ROW for EACH batch."
#                         },
#                         {
#                             "role": "user",
#                             "content": prompt
#                         }
#                     ],
#                     temperature=0.1
#                 )
                
#                 result = completion.choices[0].message.content
#                 if result:
#                     all_results.append(result)
#             except Exception as e:
#                 st.error(f"Error processing product {product_code}: {str(e)}")
        
#         product_idx += 1
#         progress_bar.progress(product_idx / total_products)
    
#     # Process the rest of the text using the standard chunking approach
#     remaining_text = text
#     for product_code in product_sections:
#         # Remove the sections we've already processed
#         product_text = "\n".join(product_sections[product_code])
#         remaining_text = remaining_text.replace(product_text, "")
    
#     if remaining_text.strip():
#         status_text = st.empty()
#         status_text.text("Processing remaining content...")
        
#         # Use existing chunking logic for the remaining text
#         tables_and_remaining = extract_tables_and_remaining(remaining_text)
        
#         for i, (table_text, is_table) in enumerate(tables_and_remaining):
#             if is_table:
#                 status_text.text(f"Processing table {i+1}/{len(tables_and_remaining)}")
                
#                 if len(table_text) // 4 < 7000:
#                     chunk_directive = "\nThis is a complete table. Extract ALL rows without skipping any."
#                     prompt = prompt_template.format(
#                         text_content=table_text,
#                         known_batches_info=known_batches_info,
#                         chunk_directive=chunk_directive
#                     )
                    
#                     try:
#                         from openai import OpenAI
#                         client = OpenAI(api_key=open_api_key)
                        
#                         completion = client.chat.completions.create(
#                             model="gpt-4o",
#                             messages=[
#                                 {
#                                     "role": "system",
#                                     "content": "You are an invoice processing assistant. Extract ALL line items and create separate rows for each batch."
#                                 },
#                                 {
#                                     "role": "user",
#                                     "content": prompt
#                                 }
#                             ],
#                             temperature=0.1
#                         )
                        
#                         result = completion.choices[0].message.content
#                         if result:
#                             all_results.append(result)
#                     except Exception as e:
#                         st.error(f"Error processing table: {str(e)}")
#                 else:
#                     table_chunks = split_table_by_rows(table_text)
                    
#                     for j, chunk in enumerate(table_chunks):
#                         status_text.text(f"Processing table {i+1}/{len(tables_and_remaining)} - chunk {j+1}/{len(table_chunks)}")
#                         chunk_directive = f"\nThis is part {j+1}/{len(table_chunks)} of a table. Extract EVERY row in this chunk."
                        
#                         prompt = prompt_template.format(
#                             text_content=chunk,
#                             known_batches_info=known_batches_info,
#                             chunk_directive=chunk_directive
#                         )
                        
#                         try:
#                             from openai import OpenAI
#                             client = OpenAI(api_key=open_api_key)
                            
#                             completion = client.chat.completions.create(
#                                 model="gpt-4o",
#                                 messages=[
#                                     {
#                                         "role": "system",
#                                         "content": "You are an invoice processing assistant. Extract ALL line items and create separate rows for each batch."
#                                     },
#                                     {
#                                         "role": "user",
#                                         "content": prompt
#                                     }
#                                 ],
#                                 temperature=0.1
#                             )
                            
#                             result = completion.choices[0].message.content
#                             if result:
#                                 all_results.append(result)
#                         except Exception as e:
#                             st.error(f"Error processing table chunk: {str(e)}")
#             else:
#                 chunks = split_text_into_chunks(table_text, chunk_size=3000)
                
#                 for j, chunk in enumerate(chunks):
#                     status_text.text(f"Processing non-table content {i+1}/{len(tables_and_remaining)} - chunk {j+1}/{len(chunks)}")
#                     chunk_directive = f"\nThis is part {j+1}/{len(chunks)} of non-table content. Look for any hidden line items."
                    
#                     prompt = prompt_template.format(
#                         text_content=chunk,
#                         known_batches_info=known_batches_info,
#                         chunk_directive=chunk_directive
#                     )
                    
#                     try:
#                         from openai import OpenAI
#                         client = OpenAI(api_key=open_api_key)
                        
#                         completion = client.chat.completions.create(
#                             model="gpt-4o",
#                             messages=[
#                                 {
#                                     "role": "system",
#                                     "content": "You are an invoice processing assistant. Extract ALL line items and create separate rows for each batch."
#                                 },
#                                 {
#                                     "role": "user",
#                                     "content": prompt
#                                 }
#                             ],
#                             temperature=0.1
#                         )
                        
#                         result = completion.choices[0].message.content
#                         if result:
#                             all_results.append(result)
#                     except Exception as e:
#                         st.error(f"Error processing non-table chunk: {str(e)}")
        
#         product_idx += 1
#         progress_bar.progress(product_idx / total_products)
    
#     progress_bar.empty()
    
#     if not all_results:
#         return None
    
#     combined_result = combine_chunked_results(all_results)
    
#     return combined_result


def process_with_stricter_instructions(text):
    return using_groq(text)

def extract_tables_and_remaining(text):
    return [(text, False)]


def split_text_into_chunks(text, chunk_size=3000):
    return [text]



def standardize_headers(headers):
    """
    Standardize header names across different PDFs
    """
    header_mappings = {
        'Customer Number': 'Customer No',
        'Customer No.': 'Customer No',
        'Supplier Name': 'Supplier',
        'Total VAT': 'VAT',
        'Total VAT or VAT': 'VAT',
        'Total Amount of the Invoice': 'Invoice Total',
        'Payer Name': 'Payer Name', 
        'Date of Invoice': 'Invoice Date'  
    }

    standard_headers = [
        'PO Number', 'Item Code', 'Description', 'UOM', 'Quantity',
        'Lot Number', 'Expiry Date', 'Mfg Date', 'Invoice No',
        'Unit Price', 'Total Price', 'Country', 'HS Code',
        'Invoice Date', 'Customer No', 'Payer Name', 'Currency',
        'Supplier', 'Invoice Total', 'VAT'
    ]


    standardized = []
    for header in headers:
        if header in header_mappings:
            standardized.append(header_mappings[header])
        else:
            standardized.append(header)

    for header in standard_headers:
        if header not in standardized:
            standardized.append(header)

    return standard_headers 
def main_app():
    display_branding()  
    
    tab1 = st.tabs(["📄 Upload & Process"])[0]
    
    with tab1:
        st.markdown(f"""
        <div style='text-align: center; margin-bottom: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 10px; border-left: 4px solid #1f77b4;'>
            <h3 style='margin: 0; color: #1f77b4;'>👋 Welcome, {st.session_state.username}!</h3>
            <p style='margin: 10px 0 0 0; color: #666;'>Ready to extract data from your PDF invoices?</p>
        </div>
        """, unsafe_allow_html=True)

        if 'edited_df' not in st.session_state:
            st.session_state.edited_df = None
        if 'saved_df' not in st.session_state:
            st.session_state.saved_df = None
        if 'processing_complete' not in st.session_state:
            st.session_state.processing_complete = False
        if 'uploaded_pdfs' not in st.session_state:
            st.session_state.uploaded_pdfs = []
        if 'grid_key' not in st.session_state:
            st.session_state.grid_key = 'data_editor_1'

        
        
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_pdfs = st.file_uploader(
                "📄 Upload PDF Invoices",
                type=[".pdf"],
                accept_multiple_files=True,
                help="Upload one or more PDF invoice files to extract data"
            )

        if uploaded_pdfs:
            st.session_state.uploaded_pdfs = uploaded_pdfs
        
        # Fixed output file name
        excel_file = "ASN_Result.xlsx"

        pdfs_to_process = st.session_state.uploaded_pdfs or uploaded_pdfs

        if pdfs_to_process:
            if st.session_state.edited_df is not None:
                try:
                    st.markdown("### 📊 Extracted and Edited Data")
                    
                    search_query = st.text_input("🔍 Search in data:", placeholder="Type to search...", key=f"search_input_{st.session_state.grid_key}")
                    
                    display_df = st.session_state.edited_df.copy()
                    
                    if search_query:
                        mask = display_df.astype(str).apply(
                            lambda x: x.str.contains(search_query, case=False)
                        ).any(axis=1)
                        display_df = display_df[mask]
                    
                    edited_df = st.data_editor(
                        display_df,
                        use_container_width=True,
                        num_rows="dynamic",
                        height=600,
                        key=st.session_state.grid_key,
                        column_config={
                            col: st.column_config.Column(
                                width="auto",
                                help=f"Edit data in column: {col}",
                                required=True
                            ) for col in display_df.columns
                        }
                    )
                    
                    st.session_state.edited_df = edited_df
                    
                    st.markdown(f"""
                    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0;'>
                        <span style='color: #1f77b4; font-weight: 600;'>📊 {len(edited_df)} rows</span> • 
                        <span style='color: #ff7f0e; font-weight: 600;'>📋 {len(edited_df.columns)} columns</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("💾 Save Changes", key="save_changes_existing"):
                        st.session_state.saved_df = edited_df.copy()
                        save_path = save_uploaded_files(
                            st.session_state.username,
                            st.session_state.uploaded_pdfs,
                            st.session_state.saved_df
                        )
                        if save_path:
                            st.success("✅ Changes saved successfully!")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            edited_df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 Download Excel File",
                            data=buffer.getvalue(),
                            file_name=excel_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_existing"
                        )
                
                except Exception as e:
                    st.error(f"Error displaying existing table: {str(e)}")
                    st.error(traceback.format_exc())
            else:
                if st.button("🚀 Extract Data from PDFs", help="Click to start processing your uploaded PDF files"):
                    try:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        total_files = len(pdfs_to_process)
                        total_rows_processed = 0
                        total_pages_processed = 0

                        all_data = []
                        all_headers = None

                        cleanup_temp_files()

                        for idx, uploaded_pdf_file in enumerate(pdfs_to_process):
                            tmp_path = None
                            try:
                                status_text.text(f"📄 Processing file {idx + 1} of {total_files}: {uploaded_pdf_file.name}")
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                                    tmp_file.write(uploaded_pdf_file.getvalue())
                                    tmp_path = tmp_file.name
                                with st.spinner(f"🔍 Extracting text from {uploaded_pdf_file.name}..."):
                                    pdf_text = extract_text_pdf(tmp_path)
                                
                                if pdf_text:
                                    with st.spinner("🤖 Processing extracted text using AI..."):
                                        invoice_info = using_groq(pdf_text)
                                        
                                        headers, data_rows = process_invoice_lines(
                                            invoice_info
                                        )
                                        
                                        if headers and data_rows:
                                            if all_headers is None:
                                                all_headers = headers
                                            
                                            all_data.extend(data_rows)
                                            
                                            total_rows_processed += len(data_rows)
                            
                            except Exception as e:
                                st.error(f"Error processing file {uploaded_pdf_file.name}: {str(e)}")
                            
                            finally:
                                if tmp_path and os.path.exists(tmp_path):
                                    try:
                                        gc.collect()
                                        os.unlink(tmp_path)
                                    except Exception as cleanup_error:
                                        st.warning(f"Could not remove temporary file {tmp_path}: {cleanup_error}")
                                        if 'cleanup_files' not in st.session_state:
                                            st.session_state.cleanup_files = []
                                        st.session_state.cleanup_files.append(tmp_path)
                            
                            progress_bar.progress((idx + 1) / total_files)
                            gc.collect()
                        
                        
                                                    
                        if all_data and all_headers:
                            try:
                                # st.write(f"DEBUG - Number of headers: {len(all_headers)}")
                                # st.write(f"DEBUG - Number of data rows: {len(all_data)}")
                                # st.write(f"DEBUG - First row length: {len(all_data[0]) if all_data else 0}")
                                
                                cleaned_data = []
                                for idx, row in enumerate(all_data):
                                    if len(row) > len(all_headers):
                                        st.write(f"DEBUG - Trimming row {idx} from {len(row)} to {len(all_headers)} columns")
                                        cleaned_data.append(row[:len(all_headers)])
                                    elif len(row) < len(all_headers):
                                        st.write(f"DEBUG - Padding row {idx} from {len(row)} to {len(all_headers)} columns")
                                        padded_row = row + [''] * (len(all_headers) - len(row))
                                        cleaned_data.append(padded_row)
                                    else:
                                        cleaned_data.append(row)
                                
                                df = pd.DataFrame(cleaned_data, columns=all_headers)
                                st.session_state.edited_df = df.copy()
                                
                                st.write(f"DEBUG - DataFrame shape: {df.shape}")
                                df = pd.DataFrame(all_data, columns=all_headers)
                                st.session_state.edited_df = df.copy()
                                
                                try:
                                    st.markdown("### 📝 Edit Extracted Data")
                                    
                                    edited_df = st.data_editor(
                                        st.session_state.edited_df,
                                        use_container_width=True,
                                        num_rows="dynamic",
                                        column_config={col: st.column_config.Column(
                                            width="auto",
                                            help=f"Edit {col}"
                                        ) for col in st.session_state.edited_df.columns},
                                        height=600,
                                        key=f'grid_{datetime.now().strftime("%Y%m%d%H%M%S")}'
                                    )
                                                            
                                    search = st.text_input("🔍 Search in table:", key="search_input")
                                    if search:
                                        mask = edited_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                                        filtered_df = edited_df[mask]
                                    else:
                                        filtered_df = edited_df 
                                    st.session_state.edited_df = edited_df
                                    st.markdown(f"**Total Rows:** {len(filtered_df)} | **Total Columns:** {len(filtered_df.columns)}")

                                    if st.button("💾 Save Table Changes", key="save_changes"):
                                        st.session_state.saved_df = edited_df.copy()
                                        save_path = save_uploaded_files(
                                            st.session_state.username,
                                            st.session_state.uploaded_pdfs,
                                            st.session_state.saved_df
                                        )
                                        if save_path:
                                            st.success("✅ Changes saved successfully and files stored!")
                                    
                                    # Single download button
                                    buffer = io.BytesIO()
                                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                        edited_df.to_excel(writer, index=False)
                                    
                                    st.download_button(
                                        label="📥 Download Excel File",
                                        data=buffer.getvalue(),
                                        file_name=excel_file,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="download_excel"
                                    )
                                    
                                except Exception as e:
                                    st.error(f"Error displaying table and buttons: {str(e)}")
                                    st.error(traceback.format_exc())
                            except Exception as e:
                                st.error(f"Error creating DataFrame: {str(e)}")
                                st.error(traceback.format_exc())
                        else:
                            st.error("No valid data could be extracted from the invoices")
                            
                    except Exception as e:
                        st.error(f"Error in main processing: {str(e)}")
                        st.error(traceback.format_exc())

    

def main():
    # Add custom CSS for modern, simple design
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 30px;
        color: white;
        text-align: center;
    }
    .stButton > button {
        background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(31, 119, 180, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f8f9fa;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        border: 1px solid #e9ecef;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
    .stFileUploader > div > div {
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        background-color: #f8f9fa;
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e9ecef;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1f77b4;
        box-shadow: 0 0 0 3px rgba(31, 119, 180, 0.1);
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%);
    }
    .stSpinner > div > div {
        border-color: #1f77b4;
        border-top-color: transparent;
    }
    </style>
    """, unsafe_allow_html=True)
    
    verify_storage_setup()
    setup_storage()
    init_user_tracking()
    
    share_hash = st.query_params.get('share')
    
    if share_hash:
        st.title("📄 Shared File Viewer")
        check_shared_file()
    else:
        main_app()
def handle_pdf_error(e, pdf_name):
    """Handle PDF processing errors with appropriate messages and actions"""
    error_msg = str(e).lower()
    
    if "poppler" in error_msg:
        st.error(f"""Error processing {pdf_name}: Poppler is not installed or not found in PATH. 
        Please ensure Poppler is properly installed on the server.""")
    elif "permission" in error_msg:
        st.error(f"Permission error while processing {pdf_name}. Please check file permissions.")
    else:
        st.error(f"Error processing {pdf_name}: {str(e)}")
    
    if st.button("🔄 Retry Processing", key=f"retry_{hash(pdf_name)}"):
        st.session_state.edited_df = None
        st.session_state.saved_df = None
        st.session_state.processing_complete = False
 
        st.rerun()

def display_branding():
    """Display company branding in a simple, clean way"""
    st.markdown("""
    <div class="main-header">
        <h1 style='margin-bottom: 10px; font-size: 3.5rem; font-weight: 300;'>Alphamed</h1>
        <h2 style='margin: 0; font-size: 1.8rem; font-weight: 300; opacity: 0.9;'>PDF Data Extractor</h2>
        <div style='margin-top: 20px; padding: 15px; background-color: rgba(255,255,255,0.1); border-radius: 10px; border: 1px solid rgba(255,255,255,0.2);'>
            <p style='margin: 0; font-size: 1.1rem; opacity: 0.9;'>Extract and process data from PDF invoices with ease</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def process_with_ocr(pdf_path, pdf_name):
    """Process PDF with OCR including error handling and recovery options"""
    """
    try:
        text = extract_text_pdf(pdf_path)
        if not text:
            st.warning(f"No text could be extracted from {pdf_name}. The file might be corrupted or empty.")
            if st.button("🔄 Retry This File", key=f"retry_empty_{hash(pdf_name)}"):
                st.session_state.edited_df = None
                st.rerun()
            return None
        return text
    except Exception as e:
        handle_pdf_error(e, pdf_name)
        return None
    """
    st.info("We are working on it now")
    return None





def process_large_pdf_text(pdf_text, groq_client):
    """
    Process large PDF text by breaking it into chunks of approximately 4K tokens each
    and sequentially sending them to the LLM API.
    
    Args:
        pdf_text (str): The complete text extracted from the PDF
        groq_client: The initialized Groq client
        
    Returns:
        str: The combined result from all chunks
    """
    import re
    
    if not pdf_text:
        return None
    
    estimated_tokens = len(pdf_text) // 4
    
    if estimated_tokens < 6000:
        return using_groq(pdf_text)
    
    chunks = []
    current_chunk = ""
    current_token_estimate = 0
    
    paragraphs = re.split(r'\n\s*\n', pdf_text)
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
            
        paragraph_token_estimate = len(paragraph) // 4
        
        if current_token_estimate + paragraph_token_estimate > 4000 and current_chunk:
            chunks.append(current_chunk)
            current_chunk = paragraph
            current_token_estimate = paragraph_token_estimate
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_token_estimate += paragraph_token_estimate
    
    if current_chunk:
        chunks.append(current_chunk)
    
    print(f"Split PDF text into {len(chunks)} chunks for processing")
    
    all_results = []
    
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)} with estimated {len(chunk)//4} tokens")
        
        chunk_result = using_groq(chunk)
        
        if chunk_result:
            all_results.append(chunk_result)
    
    if not all_results:
        return None
    
    combined_result = combine_chunked_results(all_results)
    
    return combined_result




def extract_text_pdf_with_chunking(pdf_path, groq_client):
    """
    Extract text from PDF and handle chunking for large files.
    This function handles both machine-readable and scanned PDFs.
    """
    if is_scanned_pdf(pdf_path):
        st.info("We are working on it now")
        return None
    else:
        try:
            with fitz.open(pdf_path) as pdf:
                unique_pages = {}
                for page_num, page in enumerate(pdf):
                    page_text = page.get_text()
                    content_hash = hash(page_text)
                    if content_hash not in unique_pages:
                        unique_pages[content_hash] = page_text
                
                full_text = "\n".join(unique_pages.values())
                
                return process_large_pdf_text(full_text, groq_client)
                
        except Exception as e:
            st.error(f"Error extracting text: {str(e)}")
            return None

def combine_chunked_results(results):
    """
    Intelligently combine results from multiple chunks with improved table reconstruction.
    
    Args:
        results (list): List of string results from processing each chunk
        
    Returns:
        str: Combined result with table structure
    """
    if not results:
        return ""
    
    if len(results) == 1:
        return results[0]
    
    header_row = None
    separator_row = None
    data_rows = []
    seen_data_rows_hashes = set()
    
    for result in results:
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        
        for i, line in enumerate(lines):
            if '|' not in line:
                continue
                
            if header_row is None and '|' in line:
                header_row = line
                continue
                
            if header_row is not None and separator_row is None and set(line.replace('|', '')).issubset({'-', ' '}):
                separator_row = line
                break
    
    for result in results:
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        
        header_found = False
        separator_found = False
        
        for line in lines:
            if '|' not in line:
                continue
                
            if not header_found and line == header_row:
                header_found = True
                continue
                
            if header_found and not separator_found and line == separator_row:
                separator_found = True
                continue
            
            if '|' in line and not set(line.replace('|', '')).issubset({'-', ' '}):
                cells = [cell.strip().lower() for cell in line.split('|')]
                
                signature_parts = []
                
                if len(cells) > 2 and cells[2]:
                    signature_parts.append(cells[2])
                
                if len(cells) > 3 and cells[3]:
                    signature_parts.append(cells[3][:10] if len(cells[3]) > 10 else cells[3])
                
                if signature_parts:
                    row_signature = '|'.join(signature_parts)
                    
                    if row_signature not in seen_data_rows_hashes:
                        data_rows.append(line)
                        seen_data_rows_hashes.add(row_signature)
                else:

                    data_rows.append(line)
    
    if not header_row:
        header_row = "| PO Number | Item Code | Description | UOM | Quantity | Lot Number | Expiry Date | Mfg Date | Invoice No | Unit Price | Total Price | Country | HS Code | Invoice Date | Customer No | Payer Name | Currency | Supplier | Invoice Total | VAT |"
        separator_row = "|-----------|-----------|------------|-----|----------|-----------|-------------|----------|-----------|-----------|------------|---------|---------|-------------|------------|-----------|----------|----------|--------------|-----|"
    
    table_parts = [header_row]
    
    if separator_row:
        table_parts.append(separator_row)
        
    table_parts.extend(data_rows)
    
    return '\n'.join(table_parts)




if __name__ == "__main__":

    main()

