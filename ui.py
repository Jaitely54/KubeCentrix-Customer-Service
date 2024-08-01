import streamlit as st
from streamlit_chat import message
import time
import json
from utils.setup import setup_directories, get_cwd
from rag import process_pdfs, create_vector_db, query_azure_openai, get_embedding
import numpy as np
from bank_crm import BankCRM
from utils.user_authentication import UserAuth
from bank_statement import (
    load_csv, optimize_dataframe, query_openai, execute_pandas_code, generate_summary,
)
from Dynamic.variables import api_key
import faiss
from translate import translate_text, detect_language
import openai
import speech_recognition as sr
from gtts import gTTS
import io
from pydub import AudioSegment
from pydub.playback import play

# Set up OpenAI API key
openai.api_key = api_key

# Initialize speech recognition
recognizer = sr.Recognizer()

def speech_to_text():
    with sr.Microphone() as source:
        st.write("Listening...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand that."
        except sr.RequestError:
            return "Sorry, there was an error with the speech recognition service."

def text_to_speech(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    audio = AudioSegment.from_file(fp, format="mp3")
    play(audio)

def load_environment():
    if not openai.api_key:
        st.error("No API key provided. Please set the API key in the variables.py file.")
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

local_css("Xstyle.css")

# Initialize backend components
@st.cache_resource
def initialize_backend():
    pdf_dir, output_dir, embedding_file_path = setup_directories()
    combined_text = process_pdfs(pdf_dir, output_dir)
    index, chunks = create_vector_db(combined_text, embedding_file_path)
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
        generated_code = query_openai(prompt)
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
                st.session_state.disclaimer_accepted = False
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
        credit_score = st.number_input("Credit Score (300-850)", min_value=300, max_value=850, value=300)
        account_balance = st.number_input("Initial Account Balance", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Create Account")
        if submitted:
            if auth.create_user(user_id, password, name, int(credit_score), float(account_balance)):
                st.success("User created successfully!")
                crm.add_file_to_user(user_id, "customer-protection-policy-2023.pdf")
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

    checkbox = st.checkbox("Accept to continue", key="disclaimer_checkbox")

    col1, col2 = st.columns(2)

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

def show_chat_ui():
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.image("logo-no-background.svg", width=150)
    with col2:
        st.title("VirtualBOB: your banking Assistant")
    with col3:
        tabs = st.tabs(["Setting", "Tab2", "Tab3"])

    languages = {
        'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French',
        'de': 'German', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian',
        'ja': 'Japanese', 'ko': 'Korean', 'zh-cn': 'Chinese (Simplified)'
    }
    st.session_state.preferred_lang = st.selectbox("Select your preferred language:", 
                                                   list(languages.keys()), 
                                                   format_func=lambda x: languages[x],
                                                   index=list(languages.keys()).index(st.session_state.preferred_lang))

    chat_col, profile_col = st.columns([3, 1])

    with chat_col:
        st.subheader(f"Welcome {st.session_state.user['name']}")

        if st.session_state.detected_lang != st.session_state.preferred_lang:
            st.info(f"Detected language: {languages[st.session_state.detected_lang]}")

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([0.7, 0.7, 0.7, 0.7, 2.2])
            with col1:
                temp_chat = st.toggle("Temp", key="temp_chat")
            with col2:
                if st.button("General query"):
                    st.session_state.query_type = "general_query"
                    st.experimental_rerun()
            with col4:
                if st.button("Bank statement"):
                    st.session_state.query_type = "bank_statement"
                    st.experimental_rerun()
            with col5:
                if st.button("Logout"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.experimental_rerun()

        st.subheader("Chat History")
        for i, (message_text, is_user) in enumerate(st.session_state.messages):
            message(message_text, is_user=is_user, key=str(i))
            if not is_user:
                if st.button(f"🔊 Listen", key=f"listen_{i}"):
                    text_to_speech(message_text, lang=st.session_state.preferred_lang)

        st.subheader("Ask a question:")
        user_input = st.text_input("Your question:", key="user_input_field")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎙️ Speak your question"):
                user_input = speech_to_text()
                st.session_state.user_input = user_input
                st.experimental_rerun()
        with col2:
            if st.button("Submit"):
                if user_input and user_input.strip():
                    st.session_state.messages.append((user_input, True))
                    response = handle_query(user_input, st.session_state.user, st.session_state.query_type, st.session_state.user_files)
                    st.session_state.messages.append((response, False))
                    st.experimental_rerun()

    with profile_col:
        st.subheader("Profile Information")
        if st.session_state.user:
            st.markdown(f"**Name:** {st.session_state.user['name']}")
            st.markdown(f"**User ID:** {st.session_state.user['user_id']}")
            st.markdown(f"**Account Balance:** ${st.session_state.user['account_balance']:.2f}")
        else:
            st.warning("User data not available.")

# Main UI logic
if st.session_state.user is None:
    login_form()
elif not st.session_state.disclaimer_accepted:
    show_disclaimer()
else:
    show_chat_ui()
