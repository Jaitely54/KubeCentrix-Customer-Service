import logging
import PyPDF2
import os
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.prompts import ChatPromptTemplate
from chromadb.config import Settings
import chromadb

def extract_text_from_pdf(pdf_path):
    logging.info(f"Extracting text from PDF: {pdf_path}")
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)
        text = ''
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
    return text

def process_pdfs(pdf_dir, output_dir):
    logging.info(f"Processing PDFs in directory: {pdf_dir}")
    all_texts = []
    for filename in os.listdir(pdf_dir):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_dir, filename)
            pdf_name = Path(pdf_path).stem
            logging.info(f"Processing PDF: {filename}")
            text = extract_text_from_pdf(pdf_path)
            all_texts.append(text)
            
            with open(os.path.join(output_dir, f"{pdf_name}_text.txt"), "w", encoding="utf-8") as file:
                file.write(text)
    return '\n'.join(all_texts)

def create_vector_db(combined_text, embedding_file_path):
    logging.info("Splitting text into chunks")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_text(combined_text)
    logging.info(f"Number of chunks created: {len(chunks)}")

    logging.info("Initializing HuggingFace embeddings")
    huggin_embeddings = HuggingFaceBgeEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    logging.info("Creating Chroma vector store")
    client = chromadb.PersistentClient(path=embedding_file_path, settings=Settings(anonymized_telemetry=False))
    vector_store = Chroma.from_texts(
        texts=chunks,
        embedding=huggin_embeddings,
        client=client,
        persist_directory=f"{embedding_file_path}/combined_db"
    )
    logging.info("Vector store created successfully")
    return vector_store

def setup_rag_chain(vector_db):
    logging.info("Setting up RAG chain")
    local_model = "gemma:2b"
    llm = ChatOllama(model=local_model, top_k=60)
    retriever = vector_db.as_retriever()

    systemprompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise.\n\n"
        "Context: {context}\n"
        "Customer Info: {customer_info}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", systemprompt),
        ("human", "{input}")
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    logging.info("RAG chain setup completed successfully")
    return rag_chain
