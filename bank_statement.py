import openai
import os
import pandas as pd
import numpy as np
import io
import sys
import logging
from functools import lru_cache
from dotenv import load_dotenv
import json
from tabulate import tabulate
from variables import *
from utils import *
import warnings

warnings.filterwarnings("ignore")

# Module: Logging and Configuration
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_environment():
    # load_dotenv()
    openai.api_key = 'sk-None-X2ezA4VAr2wd7eV7KpQlT3BlbkFJyd91L3bQE62CyvKs6YgX'

# Module: Data Loading and Optimization
@lru_cache(maxsize=32)
def load_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        return df.columns.tolist(), df
    except Exception as e:
        logging.error(f"Error loading CSV file: {e}")
        raise

def optimize_dataframe(df):
    for col in df.select_dtypes(include=['int', 'float']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
    
    date_columns = df.select_dtypes(include=['object']).columns[df.select_dtypes(include=['object']).apply(lambda x: pd.to_datetime(x, errors='coerce').notnull().all())]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col])
    
    return df

# Module: OpenAI Interaction
@lru_cache(maxsize=128)
def query_openai(prompt, model="gpt-3.5-turbo"):
    try:
        system_content = """You are a Python programming assistant specializing in pandas for bank data analysis. Generate executable Python code without any formatting or code blocks. The dataframe is already loaded as 'df'.
        Important guidelines:
        1. Always use print(tabulate(df, headers='keys', tablefmt='pretty')) for displaying full DataFrames as tables.
        2. Use print(tabulate(df.head(), headers='keys', tablefmt='pretty')) for large DataFrames to show only the first few rows as a table.
        3. Assume all necessary libraries (pandas, numpy, tabulate) are already imported.
        4. Always check for null values and data types before performing operations.
        5. Include basic error handling for column existence using try-except blocks.
        6. Use appropriate aggregation functions like sum, mean, count, etc. based on the query.
        7. Format currency values in Indian Rupees (Rs.) when applicable.
        8. Focus on generating accurate and relevant results without additional commentary.
        9. Do not include any code to read or load the CSV file, as the data is already in the 'df' dataframe.
        10. Ensure all code is within a try-except block to catch any potential errors.
        11. Always include code to check the dataframe's shape and column names before performing operations.
        12. Provide diagnostic information about the dataframe structure and data types when relevant.
        13. Use df.columns.str.strip() to remove any leading/trailing spaces from column names.
        14. Always print the first few rows of the dataframe and the data types of columns before performing the main analysis.
        15. For counting or analyzing text data, consider using df['column'].astype(str) to ensure all values are treated as strings.
        16. Handle date columns appropriately, converting to datetime if necessary for analysis.
        17. Provide clear, concise output that directly answers the user's query.
        18. Use vectorized operations whenever possible for better performance.
        19. Optimize memory usage by using appropriate data types and avoiding unnecessary copies.
        20. When asked to show a list or table, create a new dataframe with the relevant data and print it using tabulate.
        21. Always display monetary amounts in Indian Rupees (Rs.).
        22. For person-specific queries:
            a. Identify columns that might contain transaction details (e.g., 'Description', 'Narration', 'Particulars').
            b. Split the person's name into parts and search for each part separately in the identified columns.
            c. Use case-insensitive partial matching (df[col].str.contains(name_part, case=False, na=False)) for each name part.
            d. Combine the results to find transactions where all parts of the name are present.
            e. Show a sample of matched transactions for verification.
            f. The person name which will be in the Desription not be plaed like that, It will always be in the transaction ID like UPI ID, NEFT, POS
        23. When filtering for specific transactions, always show the total number of matches found.
        24. For amount calculations, clearly indicate whether it's a total received, total sent, or net amount.
        """
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400,
            top_p=0.95,
        )
        code = response.choices[0].message['content']
        return code.replace('```python', '').replace('```', '').strip()
    except Exception as e:
        logging.error(f"Error querying OpenAI: {e}")
        raise

# Module: Code Execution
def execute_pandas_code(code, df):
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output
    
    try:
        exec(code)
        sys.stdout = old_stdout
        return redirected_output.getvalue().strip()
    except Exception as e:
        sys.stdout = old_stdout
        logging.error(f"Error executing code: {e}")
        return f"Error executing code: {str(e)}"

# Module: Summary Generation
@lru_cache(maxsize=128)
def generate_summary(query, result, model="gpt-3.5-turbo"):
    try:
        summary_prompt = f"""
        Analyze the following query and its result from a Bank of Baroda statement analysis:

        Query: {query}

        Result:
        {result}

        Please provide a concise summary of the analysis result in plain language. 
        Explain the key findings, trends, or insights derived from the data. 
        Make sure the summary is easily understandable for someone without technical knowledge of data analysis.

        Important guidelines:   
        1. If the result contains a table with more than 5 entries, include it in your response. Otherwise, do not include the table.
        2. Do not include the entire DataFrame if it's present in the result. Only include relevant, summarized information.
        3. Always display monetary amounts in Indian Rupees (Rs.).
        4. If the result doesn't make sense or seems to be an error message, acknowledge the issue and suggest the user try rephrasing their query.

        Your response should be structured as follows:
        1. A brief textual summary of the key findings.
        2. The table (only if it contains more than 5 entries and is not the entire DataFrame).
        3. Any additional insights or recommendations based on the analysis.
        """

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI assistant specializing in explaining Bank of Baroda statement analysis results in simple terms."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.5,
            max_tokens=400,
            top_p=0.95,
        )

        return response.choices[0].message['content'].strip()
    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        raise

# Module: Chat History Management
def load_chat_history():
    try:
        with open('chat_history.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_chat_history(history):
    with open('chat_history.json', 'w') as f:
        json.dump(history, f, indent=2)

def update_chat_history(history, query, summary):
    history.append({"User": query, "AI": summary})
    if len(history) > 5:
        history.pop(0)
    save_chat_history(history)

# Module: Query Classification
def is_analysis_query(query):
    prompt = f"""
    Determine if the following user input is a specific query about bank statement analysis or a general chat message:

    User input: {query}

    Respond with only 'ANALYSIS' if it's a specific query about bank statement analysis, or 'CHAT' if it's a general chat message.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that categorizes user inputs."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=10
        )
        return response.choices[0].message['content'].strip() == 'ANALYSIS'
    except Exception as e:
        logging.error(f"Error determining query type: {e}")
        return False

# Module: Chat Response Generation
def chat_response(query, last_summary):
    prompt = f"""
    You are an AI assistant for Bank of Baroda, specialized in bank statement analysis. 
    Respond to the following user input in a friendly and helpful manner:
    
    User input: {query}
    
    If the user is making small talk or asking an unrelated question, respond politely and steer the conversation back to bank statement analysis.
    If the user is asking to explore the previous analysis further, use this summary as context: {last_summary}
    
    Remember to always stay in character as a Bank of Baroda AI assistant.
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a Bank of Baroda AI assistant specializing in bank statement analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        logging.error(f"Error generating chat response: {e}")
        return "I apologize, I'm having trouble generating a response. Could you please provide a specific question about your Bank of Baroda statement?"

# Main Function
def main():
    setup_logging()
    load_environment()
    
    # csv_path = input("Enter the path to your Bank of Baroda statement CSV file: ").strip()
    csv_path = get_cwd()
    
    try:
        headers, df = load_csv(csv_path)
        df = optimize_dataframe(df)
    except FileNotFoundError:
        logging.error(f"Error: File '{csv_path}' not found.")
        return
    except Exception as e:
        logging.error(f"An error occurred while loading the file: {e}")
        return

    logging.info(f"Loaded Bank of Baroda statement CSV file: {csv_path}")
    logging.info(f"Headers: {headers}")
    logging.info(f"Number of rows: {len(df)}")

    chat_history = load_chat_history()
    last_summary = ""

    print("\nHello! I'm the Bank of Baroda AI assistant. How can I help you today?")

    while True:
        query = input("\nUser: ").strip()
        if query.lower() == 'quit':
            print("\nThank you for using the Bank of Baroda AI assistant. Goodbye!")
            break

        if is_analysis_query(query):
            prompt = f"""
            Generate Python pandas code to analyze the following aspect of the Bank of Baroda statement:
            {query}

            The dataframe 'df' contains Bank of Baroda statement data with the following properties:
            - CSV Headers: {headers}
            - Number of rows: {len(df)}
            - Data types:
            {df.dtypes.to_string()}

            First 5 records:
            {tabulate(df.head(), headers='keys', tablefmt='pretty')}

            Last 5 records:
            {tabulate(df.tail(), headers='keys', tablefmt='pretty')}

            Ensure the code:
            1. Is directly executable and uses only the existing 'df' dataframe
            2. Is wrapped in a try-except block to handle potential errors
            3. Uses print(tabulate(...)) for formatting tables, but only for results with 5 or fewer rows
            4. For results with more than 5 rows, use print(result.to_string()) instead of tabulate
            5. Does not print the entire DataFrame; instead, summarize the results or show only relevant portions
            6. Includes relevant diagnostic information about the data
            7. Checks for the existence of necessary columns and their data types before performing operations
            8. Handles potential issues with data types, null values, or missing columns gracefully
            9. Performs data cleaning or type conversion if necessary
            10. Uses appropriate pandas functions for efficient data analysis (e.g., groupby, agg, pivot_table)
            11. Handles date-based queries effectively, if date columns are present
            12. Formats currency values in Indian Rupees (Rs.) when applicable
            13. Identifies top entries or most frequent occurrences when relevant
            14. Examines relationships between different attributes if relevant
            15. Optimizes code for performance, especially for large datasets
            16. Focuses on providing actionable insights based on the data
            17. Always prints the first few rows of the dataframe and the data types of columns before performing the main analysis
            18. Uses df.columns.str.strip() to remove any leading/trailing spaces from column names
            19. For counting or analyzing text data, considers using df['column'].astype(str) to ensure all values are treated as strings
            20. Uses vectorized operations whenever possible for better performance
            21. Always displays monetary amounts in Indian Rupees (Rs.)
            22. For person-specific queries:
                a. Identify columns that might contain transaction details (e.g., 'Description', 'Narration', 'Particulars').
                b. Split the person's name into parts and search for each part separately in the identified columns.
                c. Use case-insensitive partial matching (df[col].str.contains(name_part, case=False, na=False)) for each name part.
                d. Combine the results to find transactions where all parts of the name are present.
                e. Show a sample of matched transactions for verification.
            23. When filtering for specific transactions, always show the total number of matches found.
            24. For amount calculations, clearly indicate whether it's a total received, total sent, or net amount.
            """
            try:
                generated_code = query_openai(prompt)
                result = execute_pandas_code(generated_code, df)
                
                summary = generate_summary(query, result)
                print(f"\nAI: {summary}")

                update_chat_history(chat_history, query, summary)
                last_summary = summary

            except Exception as e:
                logging.error(f"An error occurred during the analysis: {e}")
                error_message = "I apologize, an error occurred during the analysis. Could you please try again or rephrase your query?"
                print(f"AI: {error_message}")
                
                update_chat_history(chat_history, query, error_message)

        else:
            chat_response_result = chat_response(query, last_summary)
            print(f"AI: {chat_response_result}")
            
            update_chat_history(chat_history, query, chat_response_result)

if __name__ == '__main__':
    main()