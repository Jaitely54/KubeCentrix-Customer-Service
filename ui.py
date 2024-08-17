import os
import json
import numpy as np
import streamlit as st
from bank_crm import BankCRM
from utils.user_authentication import UserAuth
from voice import speech_to_text
from utils.setup import setup_directories, get_cwd
from translate import translate_text, detect_language
from rag import process_pdfs, create_vector_db, query_azure_openai, get_embedding
from bank_statement import load_csv, optimize_dataframe, execute_pandas_code, generate_summary

# Azure OpenAI configurations
AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_MODEL = os.getenv('AZURE_OPENAI_MODEL')
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')

pwd = os.getcwd()
logo = f"{pwd}/Images/logo-no-background.svg"

def load_environment():
    if not AZURE_OPENAI_KEY or not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_MODEL or not AZURE_OPENAI_EMBEDDING_DEPLOYMENT:
        st.error("Azure OpenAI configurations are missing. Please set the required environment variables.")
        st.stop()

# Call load_environment at the start
load_environment()
st.set_page_config(layout="wide", page_title="VirtualBOB")

# Custom CSS
def local_css(file_name):
    try:
        with open(file_name, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"{file_name} file not found. Using default styles.")

local_css("style.css")

# Initialize backend components
@st.cache_resource
def initialize_backend():
    pdf_dir, output_dir, embedding_file_path = setup_directories()
    
    if not os.path.exists(pdf_dir):
        st.warning(f"PDF directory not found: {pdf_dir}. Initializing with empty data.")
        combined_text = ""
    else:
        combined_text = process_pdfs(pdf_dir, output_dir)
    
    if not combined_text:
        combined_text = "This is a placeholder text for initialization."
    
    index, chunks = create_vector_db(combined_text, embedding_file_path, 
                                     AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, 
                                     AZURE_OPENAI_EMBEDDING_DEPLOYMENT)
    crm = BankCRM()
    auth = UserAuth(crm)
    return index, chunks, crm, auth

index, chunks, crm, auth = initialize_backend()

# Load user data
try:
    with open('SampleUser.json', 'r') as file:
        user_data = json.load(file)[0]  # Assuming the first user in the list
except FileNotFoundError:
    user_data = None
except json.JSONDecodeError:
    st.error("Error decoding user data file.")
    user_data = None

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'query_type' not in st.session_state:
    st.session_state.query_type = None
if 'user_files' not in st.session_state:
    st.session_state.user_files = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'disclaimer_accepted' not in st.session_state:
    st.session_state.disclaimer_accepted = False
if 'detected_lang' not in st.session_state:
    st.session_state.detected_lang = 'en'
if 'preferred_lang' not in st.session_state:
    st.session_state.preferred_lang = 'en'

# Function to query Azure OpenAI
def query_azure_openai(prompt):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800
    }
    response = requests.post(
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_MODEL}/chat/completions?api-version=2023-05-15",
        headers=headers,
        json=data
    )
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        st.error(f"Error: {response.status_code}")
        st.error(response.text)
        return None

# Function to handle different types of queries
def handle_query(query, user_info, query_type, user_files):
    detected_lang = detect_language(query)
    st.session_state.detected_lang = detected_lang

    target_lang = 'hi' if detected_lang == 'hi' else st.session_state.preferred_lang

    if query_type == "bank_statement":
        if st.session_state.df is None:
            csv_path = get_cwd()
            headers, df = load_csv(csv_path)
            st.session_state.df = optimize_dataframe(df)

        english_query = translate_text(query, target_language='en')

        prompt = f"""
        Generate Python pandas code to analyze the following aspect of the Bank of Baroda statement:
        {english_query}

        The dataframe 'df' contains Bank of Baroda statement data with the following properties:
        - CSV Headers: {st.session_state.df.columns.tolist()}
        - Number of rows: {len(st.session_state.df)}
        - Data types:
        {st.session_state.df.dtypes.to_string()}

        First 5 records:
        {st.session_state.df.head().to_string()}

        Last 5 records:
        {st.session_state.df.tail().to_string()}

        Ensure the code follows all the guidelines provided earlier.
        """
        generated_code = query_azure_openai(prompt)
        result = execute_pandas_code(generated_code, st.session_state.df)
        summary = generate_summary(english_query, result)
        translated_summary = translate_text(summary, target_language=target_lang)
        return translated_summary
    else:
        english_query = query if detected_lang == 'en' else translate_text(query, target_language='en')

        embedding_query = get_embedding(english_query)
        D, I = index.search(np.array([embedding_query]), k=5)
        relevant_docs = [chunks[i] for i in I[0]]
        relevant_context = "\n".join(relevant_docs)

        system_prompt = ("You are an AI assistant for a bank. Your role is to provide accurate and helpful "
                         "information to customers based on the bank's policies and the customer's specific "
                         "information. Always be polite, professional, and prioritize the customer's needs.")

        full_prompt = f"System: {system_prompt}\n\nHuman: Based on the following context and user information, please answer the question: '{english_query}'\n\nContext: {relevant_context}\n\nUser Info: {user_info}\nUser Files: {user_files}\n\nAssistant:"

        response = query_azure_openai(full_prompt)

        if response:
            if target_lang != 'en':
                translated_response = translate_text(response, target_language=target_lang)
                return translated_response
            else:
                return response
        else:
            error_message = "Sorry, I couldn't generate a response. Please try again."
            return translate_text(error_message, target_language=target_lang)

# MARK: Login form


def login_form():


    st.image(logo, width=100)
    st.markdown("""
        <div class="header">
            <h1>VirtualBOB: Your Banking Assistant</h1>
        </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if auth.authenticate_user(user_id, password):
                st.session_state.user = crm.get_user_info(user_id)
                crm.update_last_login(user_id)
                st.session_state.user_files = crm.get_user_files(user_id)
                st.success("Logged in successfully!")
                st.session_state.disclaimer_accepted = False
                st.experimental_rerun()
            else:
                st.error("Authentication failed. Please try again.")

# MARK: New user registration form


def registration_form():
    st.markdown("""
        <div class="header">
            <img src="Images/logo-no-background.svg" width="150">
            <h1>VirtualBOB: Your Banking Assistant</h1>
        </div>
    """, unsafe_allow_html=True)

    with st.form("registration_form"):
        user_id = st.text_input("New User ID")
        password = st.text_input("Password", type="password")
        name = st.text_input("Full Name")
        credit_score = st.number_input(
            "Credit Score (300-850)", min_value=300, max_value=850, value=300)
        account_balance = st.number_input(
            "Initial Account Balance", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Create Account")
        if submitted:
            if auth.create_user(user_id, password, name, int(credit_score), float(account_balance)):
                st.success("User created successfully!")
                crm.add_file_to_user(
                    user_id, "customer-protection-policy-2023.pdf")
                crm.add_file_to_user(user_id, "Deposit-Policy-2023-26.pdf")
                st.info("Default files have been added to your account.")
            else:
                st.error("Failed to create user. Please try again.")

# MARK: Disclaimer


def show_disclaimer():
    st.markdown("""
        <style>
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
            .custom-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
        </style>
    """, unsafe_allow_html=True)

    st.image(logo, width=500)

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

    # Add buttons

    with col1:
        if checkbox:
            if st.button("Proceed"):
                st.session_state.disclaimer_accepted = True
                st.experimental_rerun()
        else:
            st.markdown("""
                <button class="custom-button" disabled>Proceed</button>
            """, unsafe_allow_html=True)

    with col2:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun()


# MARK: Chat UI
def show_chat_ui():


    # Header Section
    header_col1, header_col2, header_col3 = st.columns([1, 3, 1])
    
    with header_col1:
        full_name = user_data['name']
        first_name = full_name.split()[0]
        st.image(logo, width=150)
        st.subheader(f"Welcome {first_name}")
        
    with header_col2:
        st.title("VirtualBOB: Your Banking Assistant")
        
    with header_col3:
        tabs = st.tabs(["Settings", "Profile", "Statement"])
        
        with tabs[0]:
            # Preferred language selection under Settings tab
            languages = {
                'en': 'English','hi': 'Hindi','mr': 'Marathi',
                'te': 'Telugu','pa': 'Punjabi','bho': 'Bhojpuri',
                'hr': 'Haryanvi','ml': 'Malayalam','ta': 'Tamil'
                }
            st.session_state.preferred_lang = st.selectbox(
                "Select your preferred language:",
                list(languages.keys()),
                format_func=lambda x: languages[x],
                index=list(languages.keys()).index(st.session_state.preferred_lang)
            )
        with tabs[1]:
            st.info("User Profile here")
        with tabs[2]:
            st.info("Bank Statement here")

    # Chat Section
    chat_col, profile_col = st.columns([3, 1])

    with chat_col:
        # Move the button container here, just before the subheader
        st.markdown("<div class='button-container' style='display: flex; align-items: center; justify-content: space-between;'>", unsafe_allow_html=True)
        
        # Left side: Subheader
        st.markdown("<h3 style='margin: 0;'>Ask a Question:</h3>", unsafe_allow_html=True)
        
        # Right side: Buttons
        button_col1, button_col2, button_col3, button_col4 = st.columns([1, 1, 1, 1])
        with button_col1:
            temp_chat = st.toggle("Temp", key="temp_chat")
        with button_col2:
            if st.button("General Query"):
                st.session_state.query_type = "general_query"
                st.experimental_rerun()
        with button_col3:
            if st.button("Bank Statement"):
                st.session_state.query_type = "bank_statement"
                st.experimental_rerun()
        with button_col4:
            if st.button("Logout"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.experimental_rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


        # st.subheader("Chat History")
            # for i, (message_text, is_user) in enumerate(st.session_state.messages):
            #     message(message_text, is_user=is_user, key=str(i))
            #     if not is_user:
            #         if st.button(f"🔊 Listen", key=f"listen_{i}"):
            #             text_to_speech(message_text)

        st.subheader("Ask a Question:")

        # Add chat display area
        st.markdown("""
            <div id='chat-container' style='
                height: 200px; 
                width: 85%;
                overflow-y: auto; 
                margin-bottom: 1px; 
                border: 1px solid #FF6600;
                border-radius: 10px; 
                padding: 10px;
                background-color: #f9f9f9;
            '>
        """, unsafe_allow_html=True)

        # Display messages inside the container
        for i, (message_text, is_user) in enumerate(st.session_state.messages):
            if is_user:
                st.markdown(f"<div style='text-align: right;'><strong>You:</strong> {message_text}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div><strong>VirtualBOB:</strong> {message_text}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # JavaScript for auto-scrolling
        st.markdown("""
        <script>
            function scrollToBottom() {
                var chatContainer = document.getElementById('chat-container');
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            // Run on load
            scrollToBottom();
            // Set up a MutationObserver to watch for changes in the chat container
            var observer = new MutationObserver(scrollToBottom);
            observer.observe(document.getElementById('chat-container'), {childList: true, subtree: true});
        </script>
        """, unsafe_allow_html=True)

        # Input box and buttons
        input_col1, input_col2, input_col3 = st.columns([2,1,1])

        with input_col1:
            user_input = st.text_input(
                "Input Box",
                placeholder="Ask me anything about BOB services...",
                key="user_input",
                label_visibility="collapsed"
            )
        
        with input_col2:
            if st.button("Submit"):
                if user_input and user_input.strip():
                    st.session_state.messages.append((user_input, True))
                    response = handle_query(user_input, st.session_state.user, st.session_state.query_type, st.session_state.user_files)
                    st.session_state.messages.append((response, False))
                    st.experimental_rerun()
            
            
            
        with input_col3:
            if st.button("🎙️ Ask"):
                user_input = speech_to_text()
                if user_input:
                    st.session_state.user_input = user_input
                    st.experimental_rerun()
                else:
                    st.error("Sorry, I couldn't understand that. Please try again.")
            

    # Profile Section
    with profile_col:
        st.markdown("<h3 class='profile-header'>User Profile</h3>", unsafe_allow_html=True)
        st.markdown("<h4 class='profile-subheader'>Bank Details</h4>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='profile-info'>
            <p><strong>Name:</strong> {user_data['name']}</p>
            <p><strong>Email:</strong> {user_data['email']}</p>
            <p><strong>Phone:</strong> {user_data['phone_number']}</p>
            <hr>
            <p><strong>Account Number:</strong> {user_data['bank_details']['account_number']}</p>
            <p><strong>Bank Name:</strong> {user_data['bank_details']['bank_name']}</p>
            <p><strong>Branch Code:</strong> {user_data['bank_details']['branch_code']}</p>
            <p><strong>IFSC Code:</strong> {user_data['bank_details']['ifsc_code']}</p>
            <p><strong>Account Type:</strong> {user_data['bank_details']['account_type']}</p>
            <p><strong>Balance:</strong> ₹{user_data['bank_details']['balance']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer" style="position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; color: black; text-align: center; padding: 10px 0; font-size: 14px; border-top: 1px solid #FF6600;">
        <p>© 2024 KubeCentrix. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

# MARK: Main code


if __name__ == "__main__":

    if st.session_state.user is None:
        login_form()
    elif not st.session_state.disclaimer_accepted:
        show_disclaimer()
    else:
        show_chat_ui()
