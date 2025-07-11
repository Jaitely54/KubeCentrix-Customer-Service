
from utils.setup import setup_directories
from utils.user_authentication import UserAuth
from rag import process_pdfs, create_vector_db, query_azure_openai, get_embedding
import numpy as np
from bank_crm import BankCRM
from utils.user_authentication import UserAuth
from bank_statement import *
import faiss
import logging


# shashank contribution here :)
def create_new_user(auth, crm):
    print("\n--- Creating New User ---")
    user_id = input("Enter a new user ID: ")
    password = input("Enter a password: ")
    name = input("Enter your full name: ")
    
    while True:
        try:
            credit_score = int(input("Enter your credit score (300-850): "))
            if 300 <= credit_score <= 850:
                break
            else:
                print("Credit score must be between 300 and 850.")
        except ValueError:
            print("Please enter a valid number.")
    
    while True:
        try:
            account_balance = float(input("Enter your initial account balance: "))
            if account_balance >= 0:
                break
            else:
                print("Account balance cannot be negative.")
        except ValueError:
            print("Please enter a valid number.")

    print(f"Attempting to create user with ID: {user_id}")
    if auth.create_user(user_id, password, name, credit_score, account_balance):
        print("User created successfully!")
        if credit_score >= 650:
            print("Congratulations! You are eligible for a credit card.")
        else:
            print("Note: You are not eligible for a credit card at this time due to your credit score.")
        
        # Add default files for the new user
        crm.add_file_to_user(user_id, "customer-protection-policy-2023.pdf")
        crm.add_file_to_user(user_id, "Deposit-Policy-2023-26.pdf")
        print("Default files have been added to your account.")
    else:
        print("Failed to create user. See error messages above for details.")
def handle_user_session(user_info, index, chunks, crm):
    print(f"\nWelcome, {user_info['name']}!")
    print(f"Your current products: {', '.join(user_info['products'])}")
    crm.update_last_login(user_info['user_id'])
    
    user_files = crm.get_user_files(user_info['user_id'])
    print(f"Your files: {', '.join(user_files)}")
    
    # Define a system prompt
    system_prompt = ("You are an AI assistant for a bank. Your role is to provide accurate and helpful "
                     "information to customers based on the bank's policies and the customer's specific "
                     "information. Always be polite, professional, and prioritize the customer's needs.")

    while True:
        print("\nWhat type of query would you like to make?")
        print("1. General Query")
        print("2. Bank Statement Query")
        print("3. Logout")
        
        choice = input("Enter your choice (1-3): ")
        
        if choice == '3':
            print("Logging out. Goodbye!")
            break
        
        if choice not in ['1', '2']:
            print("Invalid choice. Please try again.")
            continue
        
        if choice == '2':
            # Redirect to bank statement query function
            print("Redirecting to Bank Statement Query...")
            import bank_statement
            bank_statement.main()
            continue

        query = input("Enter your query: ")
        
        if choice == '1':
            # Handle general query using the new RAG implementation
            embedding_query = get_embedding(query)
            D, I = index.search(np.array([embedding_query]), k=5)
            relevant_docs = [chunks[i] for i in I[0]]
            relevant_context = "\n".join(relevant_docs)
            
            full_prompt = f"Based on the following context and user information, please answer the question: '{query}'\n\nContext: {relevant_context}\n\nUser Info: {user_info}\nUser Files: {user_files}"
            
            response = query_azure_openai(full_prompt, system_prompt)
            if response:
                print("Assistant:", response)
            else:
                print("Sorry, I couldn't generate a response. Please try again.")
def main():
    print("Initializing Banking Assistant...")
    pdf_dir, output_dir, embedding_file_path = setup_directories()
    
    print("Processing documents...")
    combined_text = process_pdfs(pdf_dir, output_dir)
    
    print("Creating vector database...")
    index, chunks = create_vector_db(combined_text, embedding_file_path)
    
    print("Initializing CRM and authentication systems...")
    crm = BankCRM()
    
    auth = UserAuth(crm)

    print("\nWelcome to the Banking Assistant!")

    while True:
        print("\n1. Login")
        print("2. Create new user")
        print("3. Exit")
        choice = input("Enter your choice (1-3): ")

        if choice == '1':
            user_id = input("Enter your user ID: ")
            password = input("Enter your password: ")

            if auth.authenticate_user(user_id, password):
                user_info = crm.get_user_info(user_id)
                if user_info:
                    handle_user_session(user_info, index, chunks, crm)
                else:
                    print("User information not found. Please contact support.")
            else:
                print("Authentication failed. Please try again.")

        elif choice == '2':
            create_new_user(auth, crm)

        elif choice == '3':
            print("Exiting Banking Assistant. Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")

    crm.close()

if __name__ == "__main__":
    main()
