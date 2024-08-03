# rag.py

import logging
import PyPDF2
import os
from pathlib import Path
import requests
import tiktoken
import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    return len(tokenizer.encode(string))

def truncate_context(context: str, max_tokens: int) -> str:
    """Truncates the context to fit within max_tokens."""
    tokens = tokenizer.encode(context)
    if len(tokens) <= max_tokens:
        return context
    return tokenizer.decode(tokens[:max_tokens])

def extract_text_from_pdf(pdf_path):
    logging.info(f"Extracting text from PDF: {pdf_path}")
    text = ''
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
    except Exception as e:
        logging.error(f"Error extracting text from PDF {pdf_path}: {e}")
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
            
            output_path = os.path.join(output_dir, f"{pdf_name}_text.txt")
            try:
                with open(output_path, "w", encoding="utf-8") as file:
                    file.write(text)
            except Exception as e:
                logging.error(f"Error writing text to file {output_path}: {e}")
    return '\n'.join(all_texts)

def get_embedding(text, api_key, endpoint, deployment_name):
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    data = {
        "input": text
    }
    response = requests.post(
        f"{endpoint}/openai/deployments/{deployment_name}/embeddings?api-version=2023-05-15",
        headers=headers,
        json=data
    )
    if response.status_code == 200:
        return response.json()['data'][0]['embedding']
    else:
        logging.error(f"Error getting embedding: {response.status_code}")
        logging.error(response.text)
        return None

class AzureOpenAIEmbeddings:
    def __init__(self, api_key, endpoint, deployment_name):
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment_name = deployment_name

    def embed_documents(self, texts):
        return [get_embedding(text, self.api_key, self.endpoint, self.deployment_name) for text in texts]

    def embed_query(self, text):
        return get_embedding(text, self.api_key, self.endpoint, self.deployment_name)

def create_vector_db(combined_text, embedding_file_path, api_key, endpoint, deployment_name):
    logging.info("Splitting text into chunks")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_text(combined_text)
    logging.info(f"Number of chunks created: {len(chunks)}")

    logging.info("Initializing Azure OpenAI embeddings")
    azure_embeddings = AzureOpenAIEmbeddings(api_key, endpoint, deployment_name)

    logging.info("Creating FAISS vector store")
    embeddings = azure_embeddings.embed_documents(chunks)
    embedding_size = len(embeddings[0])
    index = faiss.IndexFlatL2(embedding_size)
    index.add(np.array(embeddings))

    faiss.write_index(index, embedding_file_path)
    logging.info("Vector store created successfully")
    return index, chunks

def query_azure_openai(prompt, api_key, endpoint, deployment_name):
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(
        f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2023-05-15",
        headers=headers,
        json=data
    )
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        logging.error(f"Error: {response.status_code}")
        logging.error(response.text)
        return None
