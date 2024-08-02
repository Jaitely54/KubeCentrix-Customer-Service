import logging
import PyPDF2
import os
from pathlib import Path
import requests
import tiktoken
import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from Dynamic.variables import API_KEY_Azure,ENDPOINT, EMBEDDING_DEPLOYMENT, CHAT_DEPLOYMENT, MAX_TOKENS


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

def get_embedding(text):
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY_Azure
    }
    data = {
        "input": text
    }
    response = requests.post(
        f"{ENDPOINT}/openai/deployments/{EMBEDDING_DEPLOYMENT}/embeddings?api-version=2023-05-15",
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
    def embed_documents(self, texts):
        return [get_embedding(text) for text in texts]

    def embed_query(self, text):
        return get_embedding(text)

def create_vector_db(combined_text, embedding_file_path):
    logging.info("Splitting text into chunks")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_text(combined_text)
    logging.info(f"Number of chunks created: {len(chunks)}")

    logging.info("Initializing Azure OpenAI embeddings")
    azure_embeddings = AzureOpenAIEmbeddings()

    logging.info("Creating FAISS vector store")
    embeddings = [np.array(get_embedding(chunk)) for chunk in chunks]
    embedding_size = len(embeddings[0])
    index = faiss.IndexFlatL2(embedding_size)
    index.add(np.array(embeddings))

    faiss.write_index(index, embedding_file_path)
    logging.info("Vector store created successfully")
    return index, chunks

def query_azure_openai(prompt):
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY_Azure
    }
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(
        f"{ENDPOINT}/openai/deployments/{CHAT_DEPLOYMENT}/chat/completions?api-version=2023-05-15",
        headers=headers,
        json=data
    )
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        logging.error(f"Error: {response.status_code}")
        logging.error(response.text)
        return None

def run_test():
    try:
        # Set up directories
        pdf_dir = "Docs"
        output_dir = "extracted_text"
        embedding_file_path = "embeddings/combined_index"

        # Ensure output and embedding directories exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(embedding_file_path), exist_ok=True)

        # Process PDFs
        combined_text = process_pdfs(pdf_dir, output_dir)
        logging.info("PDF processing completed")

        # Create vector database
        index, chunks = create_vector_db(combined_text, embedding_file_path)
        logging.info("Vector database created")

        # Test query
        test_query = "What is the main topic of the documents?"
        
        # Retrieve relevant context from vector store
        embedding_query = get_embedding(test_query)
        D, I = index.search(np.array([embedding_query]), k=5)  # Increased from 3 to 5
        relevant_docs = [chunks[i] for i in I[0]]
        relevant_context = "\n".join(relevant_docs)
        
        # Truncate context if necessary
        max_context_tokens = MAX_TOKENS - num_tokens_from_string(test_query) - 100  # Leave room for query and some buffer
        truncated_context = truncate_context(relevant_context, max_context_tokens)
        
        # Construct the full prompt
        full_prompt = f"Based on the following context, please answer the question: '{test_query}'\n\nContext: {truncated_context}"
        
        # Query Azure OpenAI
        response = query_azure_openai(full_prompt)

        if response:
            logging.info(f"Test Query: {test_query}")
            logging.info(f"Response: {response}")
        else:
            logging.error("Failed to get a response from Azure OpenAI")

    except Exception as e:
        logging.error(f"Error during test run: {e}")

if __name__ == "__main__":
    run_test()
