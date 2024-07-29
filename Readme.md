# Customer Service Enhancement with Generative AI

## Project Overview

This project aims to revolutionize customer service by using generative AI to deliver personalized, efficient, and proactive support. Our goal is to automate real-time responses to customer inquiries, offer tailored recommendations based on customer data, integrate smoothly with existing service platforms, and ensure top-notch security and data privacy.

## Features

- **Automated Real-Time Responses:** Uses generative AI to provide immediate, accurate responses to customer queries.
- **Personalized Recommendations:** Tailors recommendations based on customer data and interactions.
- **Integration with Existing Platforms:** Seamlessly integrates with current customer service platforms.
- **Enhanced Security and Privacy:** Adheres to the highest standards of data security and privacy.

## Installation

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/Jaitely54/KubeCentrix-Customer-Service.git
    cd KubeCentrix-Customer-Service
    ```

2. **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Project Structure

The project is organized into the following modules:

- `rag.py`: Handles the processing of PDF documents, creation of vector databases, and setup of the Retrieval-Augmented Generation (RAG) chain.
- `bank_crm.py`: Manages customer relationship management (CRM) tasks including user information and file management.
- `bank_statement.py`: Provides functionality for analyzing bank statements and generating insights.
- `utils/setup.py`: Contains utility functions for setting up directories and configurations.
- `utils/user_authentication.py`: Manages user authentication and account creation.
- `main.py`: The entry point of the application, handling user interactions, authentication, and session management.

## Workflow of the Project :


![image](https://github.com/Jaitely54/KubeCentrix-Customer-Service/assets/136069402/50f1a52e-eec2-4147-984c-4905b8898dcd)

## Usage

1. **Start the Application:**
    ```bash
    python main.py
    ```

2. **Follow the On-Screen Prompts:**
    - **Login:** Enter your user ID and password to access your account.
    - **Create New User:** Create a new user by providing required details.
    - **Handle User Session:** Interact with the system to make queries or manage files.

## Functionality

### `rag.py`

- **Extract Text from PDF:** Extracts and processes text from PDF documents.
- **Create Vector Database:** Creates a vector store for efficient retrieval of information.
- **Setup RAG Chain:** Configures the Retrieval-Augmented Generation (RAG) chain for query handling.

### `bank_crm.py`

- **User Management:** Handles user data, file management, and session updates.
- **Add Default Files:** Adds default files to a user’s account upon creation.

### `bank_statement.py`

- **Bank Statement Analysis:** Provides tools for analyzing bank statements and generating insights.

### `utils/setup.py`

- **Setup Directories:** Sets up necessary directories for storing files and embeddings.

### `utils/user_authentication.py`

- **User Authentication:** Manages user login and account creation processes.

## Configuration

- **API Keys:** Ensure you have set up the API keys for OpenAI and other services in the `Dynamic/variables.py` file.
- **File Paths:** Update paths for PDFs and embeddings in the `main.py` as needed.


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- **LangChain:** For text splitting and vector store creation.
- **HuggingFace:** For embeddings.
- **Chroma:** For vector database management.
- **PyPDF2:** For PDF text extraction.





