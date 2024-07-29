import streamlit as st
from streamlit_chat import message
import time
import json

# Set page config
st.set_page_config(layout="wide", page_title="SavedUI")

# Custom CSS
def local_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("Style/Chat.css")

# Load user data
with open('Json/sampleuser.json', 'r') as file:
    user_data = json.load(file)[0]  # Assuming the first user in the list

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Header
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    st.image("logo-no-background.svg", width=150)
with col2:
    st.title("VirtualBOB: your banking Assistant")
with col3:
    tabs = st.tabs(["Setting", "Tab2", "Tab3"])

# Main content
chat_col, profile_col = st.columns([3, 1])

# Chat interface
with chat_col:
    st.subheader(f"Welcome {user_data['name']}")
    
    temp_chat = st.toggle("Temp chat")
    
    # Chat messages display area
    chat_container = st.container()
    
    # Function to display messages
    def display_messages():
        with chat_container:
            for i, msg in enumerate(st.session_state.messages):
                message(msg['content'], is_user=msg['is_user'], key=f"msg_{i}")
    
    # Display existing messages
    display_messages()
    
    # Input field
    user_input = st.text_input("Ask me anything about bob services...", key="user_input")
    
    # Send button
    if st.button("Send"):
        if user_input:
            # Add user message to chat
            st.session_state.messages.append({"content": user_input, "is_user": True})
            
            # Simulate bot response
            with st.spinner("VirtualBOB is typing..."):
                time.sleep(1)  # Simulate processing time
                bot_response = f"Thank you for your question: '{user_input}'. How can I assist you further?"
                st.session_state.messages.append({"content": bot_response, "is_user": False})
            
            # Rerun to update the chat display
            st.experimental_rerun()

# Profile section
with profile_col:
    st.markdown("<h3 class='profile-header'>User Profile</h3>", unsafe_allow_html=True)
    
    st.markdown("<h4 class='profile-subheader'>Personal Information</h4>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='profile-info'>
        <p><strong>Name:</strong> {user_data['name']}</p>
        <p><strong>Email:</strong> {user_data['email']}</p>
        <p><strong>Phone:</strong> {user_data['phone_number']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h4 class='profile-subheader'>Bank Details</h4>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='profile-info'>
        <p><strong>Account Number:</strong> {user_data['bank_details']['account_number']}</p>
        <p><strong>Bank Name:</strong> {user_data['bank_details']['bank_name']}</p>
        <p><strong>Branch Code:</strong> {user_data['bank_details']['branch_code']}</p>
        <p><strong>IFSC Code:</strong> {user_data['bank_details']['ifsc_code']}</p>
        <p><strong>Account Type:</strong> {user_data['bank_details']['account_type']}</p>
        <p><strong>Balance:</strong> ${user_data['bank_details']['balance']:.2f}</p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    <p>© 2024 KubeCentrix. All rights reserved.</p>
</div>
""", unsafe_allow_html=True)