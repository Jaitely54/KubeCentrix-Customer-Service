import streamlit as st

# Set the page title and layout
st.set_page_config(page_title="Banking Chatbot Disclaimer", layout="centered")

# Add custom CSS
st.markdown("""
    <style>
        .main {
            background-color: white;
        }
        .header {
            text-align: center;
        }
        .logo {
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 150px;
        }
        .disclaimer {
            color: black;
            font-size: 16px;
            margin: 20px 0;
            text-align: left;
        }
        .disclaimer span {
            color: #FF4B4B;
            font-weight: bold;
        }
        .checkbox-container {
            display: flex;
            align-items: center;
            font-size: 16px;
            margin: 20px 0;
        }
        .checkbox-container input {
            margin-right: 10px;
        }
        .checkbox-text {
            color: black;
        }
        .button-container {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
        }
        .custom-button {
            width: 100%;
            background-color: #f0f2f6;
            color: black;
            border: none;
            padding: 10px;
            font-size: 16px;
            cursor: pointer;
        }
        .custom-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
    </style>
""", unsafe_allow_html=True)

st.image("Images/logo-no-background.svg", width=600)

# Add disclaimer text
st.markdown("""
<div class="header">
    <div class="disclaimer">
        <span>Disclaimer:</span> This AI-powered chatbot is here to help with your banking questions. While we aim to offer precise and useful answers, the information provided by the chatbot may not always be up-to-date or completely accurate. This version is not intended for production use, just for testing out early features that are still in development. AI Generated Responses are not 100% accurate and it is required to double-check the facts.
    </div>
</div>
""", unsafe_allow_html=True)

# Checkbox for acceptance
checkbox = st.checkbox("Accept to continue")

# Create two columns for buttons
col1, col2 = st.columns(2)

# Add buttons to the columns
with col1:
    if checkbox:
        st.markdown("""
            <button class="custom-button" onclick="alert('Proceeding...')">Proceed</button>
        """, unsafe_allow_html=True)
        # st.session_state.page = "page2"
        # st.experimental_rerun()
    else:
        st.markdown("""
            <button class="custom-button" disabled>Proceed</button>
        """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <button class="custom-button" onclick="alert('Logging out...')">Logout</button>
    """, unsafe_allow_html=True)
# Display page based on session state
