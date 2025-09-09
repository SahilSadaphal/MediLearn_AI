import streamlit as st
import requests
import time

# Configure page
st.set_page_config(
    page_title="MediLearn AI",
    page_icon="🏥",
    layout="centered"
)

# Backend API configuration
API_BASE_URL = "http://localhost:8000"

def login_user(username, password):
    """Login user and get cookies"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/login/",
            data={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            # Save cookies from response
            cookies = response.cookies.get_dict()
            return response.json(), cookies
        else:
            return None, None
            
    except requests.RequestException as e:
        st.error(f"Connection error: {e}")
        return None, None

def upload_pdf(file, cookies):
    """Upload PDF with authentication cookies"""
    try:
        files = {"file": file}
        response = requests.post(
            f"{API_BASE_URL}/upload-pdf/",
            files=files,
            cookies=cookies
        )
        
        return response.status_code, response.json()
        
    except requests.RequestException as e:
        st.error(f"Upload error: {e}")
        return None, None

def main():
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'cookies' not in st.session_state:
        st.session_state.cookies = {}

    # Show appropriate page based on login status
    if st.session_state.logged_in:
        show_dashboard()
    else:
        show_login()

def show_login():
    """Display login form"""
    st.title("🏥 MediLearn AI")
    st.subheader("Login")
    
    # Check if backend is running
    try:
        requests.get(f"{API_BASE_URL}/docs", timeout=3)
    except:
        st.error("❌ Backend server not running. Start with: `uvicorn main:app --reload`")
        return

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username and password:
                with st.spinner("Logging in..."):
                    user_data, cookies = login_user(username, password)
                
                if user_data and cookies:
                    st.session_state.logged_in = True
                    st.session_state.user_data = user_data
                    st.session_state.cookies = cookies
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Please enter username and password")
    
    # Demo info
    with st.expander("Demo Account"):
        st.info("Create an admin user in your database first")

def show_dashboard():
    """Display main dashboard with two buttons"""
    user_data = st.session_state.user_data
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏥 MediLearn AI Dashboard")
        st.caption(f"Welcome! Role: {user_data.get('role', 'user')}")
    
    with col2:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_data = {}
            st.session_state.cookies = {}
            st.rerun()
    
    st.markdown("---")
    
    # Two main buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 Upload PDF", use_container_width=True, type="primary"):
            st.session_state.page = "upload"
    
    with col2:
        if st.button("💬 Chat", use_container_width=True, type="secondary"):
            st.session_state.page = "chat"
    
    # Show selected page content
    if hasattr(st.session_state, 'page'):
        if st.session_state.page == "upload":
            show_upload_page()
        elif st.session_state.page == "chat":
            show_chat_page()

def show_upload_page():
    """Show PDF upload page"""
    st.markdown("---")
    st.subheader("📁 Upload PDF")
    
    # Check if user is admin
    user_role = st.session_state.user_data.get('role', '')
    if user_role != 'admin':
        st.error("🚫 Unauthorized: Only administrators can upload PDFs")
        st.info(f"Your role: {user_role}")
        return
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file", 
        type=['pdf'],
        help="Upload PDF files to the knowledge base"
    )
    
    if uploaded_file:
        st.write("**File details:**")
        st.write(f"- Name: {uploaded_file.name}")
        st.write(f"- Size: {uploaded_file.size} bytes")
        
        if st.button("Upload PDF", type="primary"):
            with st.spinner("Uploading..."):
                status_code, response = upload_pdf(uploaded_file, st.session_state.cookies)
            
            if status_code == 201:
                st.success("✅ PDF uploaded successfully!")
                st.json(response)
            elif status_code == 409:
                st.warning("⚠️ File already exists")
            elif status_code == 413:
                st.error("❌ File too large (max 10MB)")
            elif status_code == 401:
                st.error("❌ Unauthorized - please login again")
                st.session_state.logged_in = False
                st.rerun()
            else:
                st.error("❌ Upload failed")
                if response:
                    st.json(response)

def show_chat_page():
    """Show chat interface"""
    st.markdown("---")
    st.subheader("💬 Chat with AI")
    
    # Simple chat interface
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Simple AI response (you can integrate with your WebSocket later)
        with st.chat_message("assistant"):
            response = f"This is a demo response to: '{prompt}'"
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.info("💡 **Note:** This is a simple demo. Integrate with your WebSocket endpoint for real AI responses.")

if __name__ == "__main__":
    main()
