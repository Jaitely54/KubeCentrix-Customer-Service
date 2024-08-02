# Bank Statement Analyzer
## Overview
This Python script provides an interactive AI assistant for analyzing Bank of Baroda statements. It uses OpenAI's GPT model to interpret user queries, generate appropriate pandas code for data analysis, and present results in a user-friendly manner.

## Features
- **CSV Loading and Optimization:** Efficiently loads and optimizes Bank of Baroda statement data from CSV files.
- **AI-Powered Analysis:** Utilizes OpenAI's GPT model to interpret user queries and generate pandas code for analysis.
- **Data Visualization:** Presents analysis results using tabulate for clear, formatted output.
- **Chat Functionality:**  Handles both analysis queries and general chat interactions.
- **Error Handling:** Robust error handling for data loading, code execution, and API interactions.
- **Logging:**  Comprehensive logging for debugging and tracking.

## Main Components
### Data Handling

- `load_csv():` Loads the CSV file and returns headers and DataFrame.
- `optimize_dataframe():` Optimizes the DataFrame for efficient processing.

### OpenAI Interaction
- `query_openai():` Sends prompts to OpenAI API and retrieves generated code.
- `generate_summary():` Creates human-readable summaries of analysis results.

### Code Execution

- `execute_pandas_code():` Safely executes generated pandas code.

### Chat Functionality

- `is_analysis_query():` Determines if a user query is for analysis or general chat.
- `chat_response():` Generates chat responses for non-analysis queries.

### History Management

- `load_chat_history(), save_chat_history(), update_chat_history()`: Manage conversation history.

### Usage
**Run the script and follow the prompts:**

```python
 bank_statement_analyzer.py
 ```

Enter the path to your Bank of Baroda statement CSV file when prompted. Then, interact with the AI assistant by typing your queries.
**Example queries:**

- "What was my total spending last month?"
- "Show me all transactions above 10,000 rupees."
- "Who are my top 5 payees?"

Type 'quit' to exit the program.

## Requirements

- Python 3.x
- pandas
- openai
- tabulate

(Note: Detailed installation instructions are not included as per your request.)

### Important Notes

- Ensure your OpenAI API key is properly set up in the api_key variable.
- The script assumes a specific format for Bank of Baroda statements. Adjustments may be needed for different formats.
- Always review the generated analysis for accuracy, especially for financial decisions.

### Disclaimer
This tool is for analysis purposes only. Always verify important financial information with official Bank of Baroda statements and consult with financial professionals for advice.