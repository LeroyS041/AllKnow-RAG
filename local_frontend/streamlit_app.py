import streamlit as st
import os
import requests
from pathlib import Path

# Streamlit talks to backend via HTTP API only

from assets.styling import apply_styling, render_user_message, render_ai_message

# Page config
st.set_page_config(
    page_title="AllKnow RAG Agent",
    page_icon="📚",
    layout="wide"
)

# Apply custom styling
apply_styling()

# API endpoint (backend running separately)
API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")

# Check if backend is reachable
try:
    health_check = requests.get(f"{API_BASE}/health", timeout=5)
    if health_check.status_code != 200:
        st.error(f"❌ Backend API is not healthy. Status: {health_check.status_code}")
        st.stop()
    
    backend_info = health_check.json()
    environment = backend_info.get("environment", "unknown")
    
    # Only allow local environment
    if environment != "local":
        st.error("⚠️ Streamlit UI is only available in LOCAL mode.")
        st.info("For cloud deployment, use the API directly via `/docs` or REST clients.")
        st.stop()
        
except requests.exceptions.RequestException as e:
    st.error(f"❌ Cannot connect to backend API at {API_BASE}")
    st.error(f"Error: {str(e)}")
    st.info("Make sure the backend is running: `docker-compose up backend`")
    st.stop()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_pdfs" not in st.session_state:
    st.session_state.uploaded_pdfs = set()

if "processed_urls" not in st.session_state:
    st.session_state.processed_urls = set()

# Main UI
st.title("📚🔎🌍 AllKnow ✨ RAG 🤖 Agent")
st.markdown("<br>", unsafe_allow_html=True)

st.subheader("👋 Hi! I'm your RAG-powered AI agent. Ask me about your PDFs, web pages, or the latest from Google! 😊")
st.markdown("___")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Show backend info
    st.info(f"**Environment:** {backend_info.get('environment', 'N/A').upper()}")
    st.info(f"**Vector Store:** {backend_info.get('vector_store', 'N/A').upper()}")
    
    st.markdown("---")
    
    # Re-upload control
    allow_reupload = st.checkbox("Allow re-upload/re-process", value=False)
    
    if not allow_reupload:
        st.warning("ℹ️ Re-uploading PDFs or re-processing URLs is disabled by default.")
    else:
        st.success("✅ Re-upload and re-process enabled")
    
    st.markdown("---")
    
    # PDF Upload
    st.subheader("📄 Upload PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        key="pdf_uploader"
    )
    
    if uploaded_file is not None:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        
        if file_id not in st.session_state.uploaded_pdfs or allow_reupload:
            with st.spinner("Processing PDF..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    params = {"force_reprocess": allow_reupload}
                    
                    response = requests.post(
                        f"{API_BASE}/pdf/upload",
                        files=files,
                        params=params,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data['message']}")
                        st.info(f"Stored {data['chunks_stored']} chunks")
                        st.session_state.uploaded_pdfs.add(file_id)
                    elif response.status_code == 409:
                        st.warning("⚠️ This PDF has already been uploaded and processed.")
                        st.info("💡 Enable 'Allow re-upload' to process it again.")
                    else:
                        st.error(f"❌ Upload failed: {response.text}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("ℹ️ This PDF was already uploaded in this session. Enable re-upload to process again.")
    
    st.markdown("---")
    
    # Web Scraping
    st.subheader("🌐 Scrape Web Page")
    url_input = st.text_input("Enter URL", key="url_input")
    
    if st.button("Scrape", key="scrape_button"):
        url = url_input.strip()
        
        if not url:
            st.warning("⚠️ Please enter a URL")
        elif not url.startswith(('http://', 'https://')):
            st.error("❌ URL must start with http:// or https://")
        elif url not in st.session_state.processed_urls or allow_reupload:
            with st.spinner("Scraping web page..."):
                try:
                    params = {"force_reprocess": allow_reupload}
                    response = requests.post(
                        f"{API_BASE}/web/scrape",
                        json={"url": url},
                        params=params,
                        timeout=60
                    )
                    
                    if response.status_code in (200, 202):
                        st.success("✅ Web page scraping started!")
                        st.session_state.processed_urls.add(url)
                    elif response.status_code == 409:
                        st.warning("⚠️ This URL has already been processed.")
                        st.info("💡 Enable 'Allow re-process' to scrape it again.")
                    else:
                        st.error(f"❌ Scraping failed: {response.text}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("ℹ️ This URL was already processed in this session. Enable re-process to scrape again.")
    
    st.markdown("---")
    
    # Stats
    st.subheader("📊 Stats")
    st.metric("PDFs Uploaded", len(st.session_state.uploaded_pdfs))
    st.metric("URLs Processed", len(st.session_state.processed_urls))
    st.metric("Messages", len(st.session_state.messages))

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        render_user_message(message["content"])
    else:
        render_ai_message(message["content"])

# Chat input
if query := st.chat_input("Enter your query..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": query})
    render_user_message(query)
    
    # Generate response via API
    with st.spinner("🤔 Thinking..."):
        try:
            response = requests.post(
                f"{API_BASE}/agent/chat",
                json={"input": query},
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                output = data.get("output", "No response from agent")
            else:
                output = f"❌ Error: {response.text}"
        except Exception as e:
            output = f"❌ Sorry, I encountered an error: {str(e)}"
    
    # Add AI response
    st.session_state.messages.append({"role": "assistant", "content": output})
    render_ai_message(output)
    
    # Force rerun to display new messages
    st.rerun()