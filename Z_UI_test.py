import streamlit as st
from streamlit_chat import message
import time
import json
from utils.setup import setup_directories, get_cwd
from rag import process_pdfs, create_vector_db, setup_rag_chain
from bank_crm import BankCRM
from utils.user_authentication import UserAuth
from bank_statement import (
    load_csv, optimize_dataframe, query_openai, execute_pandas_code, generate_summary,
)
from Dynamic.variables import api_key
import openai

# Set the API key for OpenAI
openai.api_key = api_key


def load_environment():
    if not openai.api_key:
        raise ValueError(
            "No API key provided. Please set the API key in the variables.py file.")


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


local_css("Xstyle.css")

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

# Load user data
try:
    with open('chatui/sample.json', 'r') as file:
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
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""
if 'disclaimer_accepted' not in st.session_state:
    st.session_state.disclaimer_accepted = False

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
    st.markdown("""
        <div class="header">
            <img src="logo-no-background.svg" width="150">
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
                st.session_state.disclaimer_accepted = False  # Reset disclaimer state
                st.experimental_rerun()
            else:
                st.error("Authentication failed. Please try again.")

# New user registration form


def registration_form():
    st.markdown("""
        <div class="header">
            <img src="logo-no-background.svg" width="150">
            <h1>VirtualBOB: Your Banking Assistant</h1>
        </div>
    """, unsafe_allow_html=True)

    with st.form("registration_form"):
        user_id = st.text_input("New User ID")
        password = st.text_input("Password", type="password")
        name = st.text_input("Full Name")
        credit_score = st.number_input(
            "Credit Score (300-850)", min_value=300, max_value=850)
        account_balance = st.number_input(
            "Initial Account Balance", min_value=0.0)
        submitted = st.form_submit_button("Create Account")
        if submitted:
            if auth.create_user(user_id, password, name, credit_score, account_balance):
                st.success("User created successfully!")
                crm.add_file_to_user(
                    user_id, "customer-protection-policy-2023.pdf")
                crm.add_file_to_user(user_id, "Deposit-Policy-2023-26.pdf")
                st.info("Default files have been added to your account.")
            else:
                st.error("Failed to create user. Please try again.")

# Function to show disclaimer page


def show_disclaimer():
    st.markdown("""
        <div class="header">
            <img src="logo-no-background.svg" width="150">
            <h1>VirtualBOB: Your Banking Assistant</h1>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="disclaimer">
            <span>Disclaimer:</span> This AI-powered chatbot is here to help with your banking questions. While we aim to offer precise and useful answers, the information provided by the chatbot may not always be up-to-date or completely accurate. This version is not intended for production use, just for testing out early features that are still in development. AI Generated Responses are not 100% accurate and it is required to double-check the facts.
        </div>
    """, unsafe_allow_html=True)

    # Checkbox for acceptance
    checkbox = st.checkbox("Accept to continue", key="disclaimer_checkbox")

    # Create two columns for buttons
    col1, col2 = st.columns(2)

    # Add buttons to the columns
    with col1:
        if checkbox:
            if st.button("Proceed"):
                st.session_state.disclaimer_accepted = True
                st.experimental_rerun()  # Refresh to show chat UI
        else:
            st.markdown("""
                <button class="custom-button" disabled>Proceed</button>
            """, unsafe_allow_html=True)

    with col2:
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.messages = []
            st.session_state.query_type = None
            st.session_state.user_files = None
            st.session_state.df = None
            st.session_state.disclaimer_accepted = False
            st.experimental_rerun()  # Refresh to go back to login page

# Function to show chat UI


def show_chat_ui():
    # Header
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.image("logo-no-background.svg", width=150)
    with col2:
        st.title("VirtualBOB: Your Banking Assistant")
    with col3:
        st.write("")  # Placeholder for tabs if needed

    # Main content
    chat_col, profile_col = st.columns([3, 1])

    with chat_col:
        if user_data:
            st.subheader(f"Welcome {user_data.get('name', 'User')}")
        else:
            st.subheader("Welcome User")

        # Buttons row
        with st.container():
            col1, col2, col3, col4, col5 = st.columns(
                [0.7, 0.7, 0.7, 0.7, 2.2])
            with col1:
                st.toggle("Temp", key="temp_chat")
            with col2:
                if st.button("General query"):
                    st.session_state.query_type = "general"
            with col3:
                if st.button("Personal Query"):
                    st.session_state.query_type = "bank_statement"
            with col4:
                if st.button("Logout"):
                    st.session_state.user = None
                    st.session_state.messages = []
                    st.session_state.query_type = None
                    st.session_state.user_files = None
                    st.session_state.df = None
                    st.session_state.disclaimer_accepted = False
                    st.experimental_rerun()

        # Display previous chat messages
        for msg in st.session_state.messages:
            message(msg["content"], is_user=msg["is_user"])
        st.markdown(
            "<style>.stTextInput>div>div>input { width: calc(100% - 80px) !important; }</style>", unsafe_allow_html=True)


    user_input = st.text_input("Ask me anything about bob services...",
                            value=st.session_state.get('user_input', ''))
    if st.button("Send", key="send_button"):
        st.session_state.user_input = user_input
        st.session_state.messages.append({"content": user_input, "is_user": True})
        # Simulate bot response
        with st.spinner("VirtualBOB is typing..."):
            bot_response = handle_query(user_input, st.session_state.user,
                                        st.session_state.query_type, st.session_state.user_files)
            st.session_state.messages.append(
                {"content": bot_response, "is_user": False})
        st.experimental_rerun()

               # Function to show profile information and bank details
def show_profile_info():
    profile_col = st.columns([3, 1])[1]
    with profile_col:
        st.markdown("<h3 class='profile-header'>User Profile</h3>", unsafe_allow_html=True)

        st.markdown("<h4 class='profile-subheader'>Personal Information</h4>", unsafe_allow_html=True)
        if user_data:
            st.markdown(f"""
            <div class='profile-info'>
                <p><strong>Name:</strong> {user_data.get('name', 'N/A')}</p>
                <p><strong>Email:</strong> {user_data.get('email', 'N/A')}</p>
                <p><strong>Phone:</strong> {user_data.get('phone_number', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<h4 class='profile-subheader'>Bank Details</h4>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class='profile-info'>
                <p><strong>Account Number:</strong> {user_data.get('bank_details', {}).get('account_number', 'N/A')}</p>
                <p><strong>Bank Name:</strong> {user_data.get('bank_details', {}).get('bank_name', 'N/A')}</p>
                <p><strong>Branch Code:</strong> {user_data.get('bank_details', {}).get('branch_code', 'N/A')}</p>
                <p><strong>IFSC Code:</strong> {user_data.get('bank_details', {}).get('ifsc_code', 'N/A')}</p>
                <p><strong>Account Type:</strong> {user_data.get('bank_details', {}).get('account_type', 'N/A')}</p>
                <p><strong>Balance:</strong> ${user_data.get('bank_details', {}).get('balance', 0.0):.2f}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("User data is not available.")

# Main code block
if st.session_state.user:
     # Show user profile and bank details
    if st.session_state.disclaimer_accepted:
        show_chat_ui()
        show_profile_info() 
    else:
        show_disclaimer()
else:
    login_tab, registration_tab = st.tabs(["Login", "Register"])
    with login_tab:
        login_form()
    with registration_tab:
        registration_form()

# Footer
footer = """
<div class="footer">
    <p>© 2024 KubeCentrix. All rights reserved.</p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)