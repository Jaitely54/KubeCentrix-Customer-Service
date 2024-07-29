
import streamlit as st
# from streamlit_chat import message
# import time
# import json
from utils.setup import setup_directories, get_cwd
from rag import process_pdfs, create_vector_db, setup_rag_chain
from bank_crm import BankCRM
from utils.user_authentication import UserAuth
# import bank_statement
from bank_statement import (
    load_csv, optimize_dataframe, query_openai, execute_pandas_code, generate_summary,
    # is_analysis_query, chat_response, update_chat_history
)
from Dynamic.variables import api_key
import openai
from utils.voice import text_to_speech, speech_to_text

# Set the API key for OpenAI
openai.api_key = api_key

def load_environment():
    if not openai.api_key:
        raise ValueError("No API key provided. Please set the API key in the variables.py file.")

# Call load_environment at the start
load_environment()
st.set_page_config(layout="wide", page_title="VirtualBOB-Chat")

# Initialize backend components
@st.cache_resource
def initialize_backend():
    pdf_dir, output_dir, embedding_file_path = setup_directories()
    combined_text = process_pdfs(pdf_dir, output_dir)
    vector_db = create_vector_db(combined_text, embedding_file_path)
    rag_chain = setup_rag_chain(vector_db)
    crm = BankCRM()
    auth = UserAuth(crm)
    return rag_chain, crm, auth

rag_chain, crm, auth = initialize_backend()

# Custom CSS
def local_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

try:
    local_css("style.css")
except FileNotFoundError:
    st.warning("style.css file not found. Using default styles.")

# Additional CSS for scrollable chat container
scrollable_css = """
<style>
.chat-container {
    max-height: 400px;
    overflow-y: auto;
}
.chat-message {
    padding: 10px;
    border-radius: 5px;
    margin-bottom: 10px;
}
.user-message {
    background-color: #DCF8C6;
    text-align: right;
}
.bot-message {
    background-color: #F1F0F0;
    text-align: left;
}
</style>
"""
st.markdown(scrollable_css, unsafe_allow_html=True)

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
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

# Function to handle different types of queries
def handle_query(query, user_info, query_type, user_files):
    if query_type == "bank_statement":
        if st.session_state.df is None:
            # Load the CSV file from the backend
            csv_path = get_cwd()  # Assuming this returns the path to the CSV file
            headers, df = load_csv(csv_path)
            st.session_state.df = optimize_dataframe(df)
        
        prompt = f"""
        Generate Python pandas code to analyze the following aspect of the Bank of Baroda statement:
        {query}

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
        generated_code = query_openai(prompt)
        result = execute_pandas_code(generated_code, st.session_state.df)
        summary = generate_summary(query, result)
        return summary
    else:
        response = rag_chain.invoke({
            "input": query,
            "customer_info": str(user_info),
            "user_files": str(user_files)
        })
        return response["answer"]

# Login form
def login_form():
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
            else:
                st.error("Authentication failed. Please try again.")

# New user registration form
def registration_form():
    with st.form("registration_form"):
        user_id = st.text_input("New User ID")
        password = st.text_input("Password", type="password")
        name = st.text_input("Full Name")
        credit_score = st.number_input("Credit Score (300-850)", min_value=300, max_value=850)
        account_balance = st.number_input("Initial Account Balance", min_value=0.0)
        submitted = st.form_submit_button("Create Account")
        if submitted:
            if auth.create_user(user_id, password, name, credit_score, account_balance):
                st.success("User created successfully!")
                crm.add_file_to_user(user_id, "customer-protection-policy-2023.pdf")
                crm.add_file_to_user(user_id, "Deposit-Policy-2023-26.pdf")
                st.info("Default files have been added to your account.")
            else:
                st.error("Failed to create user. Please try again.")

# Main UI
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    st.image("logo-no-background.svg", width=150)
with col2:
    st.title("VirtualBOB: Your Banking Assistant")
with col3:
    tabs = st.tabs(["Settings", "Tab2", "Tab3"])

if not st.session_state.user:
    login_tab, register_tab = st.tabs(["Login", "Register"])
    with login_tab:
        login_form()
    with register_tab:
        registration_form()
else:
    chat_col, profile_col = st.columns([3, 1])

    with chat_col:
        st.subheader(f"Welcome {st.session_state.user['name']}!")
        st.write(f"Your current products: {', '.join(st.session_state.user['products'])}")
        st.write(f"Your files: {', '.join(st.session_state.user_files)}")
        
        # Query type selection
        st.write("\nWhat type of query would you like to make?")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("1. General Query"):
                st.session_state.query_type = "general"
        with col2:
            if st.button("2. Bank Statement Query"):
                st.session_state.query_type = "bank_statement"
        with col3:
            if st.button("3. Logout"):
                st.session_state.user = None
                st.session_state.messages = []
                st.session_state.query_type = None
                st.session_state.user_files = None
                st.session_state.df = None
                st.experimental_rerun()
        
        # Chat display area
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for msg in st.session_state.messages:
            message_class = "user-message" if msg['is_user'] else "bot-message"
            st.markdown(f'<div class="chat-message {message_class}">{msg["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Input field and buttons
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            text_input = st.text_input("Enter your query:", key="text_input")
        with col2:
            if st.button("🎤", help="Click to use voice input"):
                with st.spinner("Listening..."):
                    voice_input = speech_to_text()
                    if voice_input:
                        st.session_state.user_input = voice_input
                        st.experimental_rerun()
        with col3:
            if st.button("Send"):
                st.session_state.user_input = text_input
                if st.session_state.user_input and st.session_state.query_type:
                    user_input = st.session_state.user_input
                    st.session_state.messages.append({"content": user_input, "is_user": True})
                    with st.spinner("VirtualBOB is typing..."):
                        bot_response = handle_query(user_input, st.session_state.user, st.session_state.query_type, st.session_state.user_files)
                        st.session_state.messages.append({"content": bot_response, "is_user": False})
                    st.session_state.user_input = ""
                    st.experimental_rerun()
                elif not st.session_state.query_type:
                    st.warning("Please select a query type (General or Bank Statement) before sending a message.")

        # Text-to-Speech button
        if st.button("🔊"):
            text_to_speech(st.session_state.user_input)

    with profile_col:
        st.subheader("Profile")
        st.write(f"Name: {st.session_state.user['name']}")
        st.write(f"User ID: {st.session_state.user['user_id']}")
        st.write(f"Credit Score: {st.session_state.user['credit_score']}")
        st.write(f"Account Balance: ${st.session_state.user['account_balance']:.2f}")
        st.write(f"Products: {', '.join(st.session_state.user['products'])}")

# Footer
st.markdown("© 2024 KubeCentrix. All rights reserved.", unsafe_allow_html=True)
