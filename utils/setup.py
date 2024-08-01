import os
from pathlib import Path

def setup_directories():
    cwd = os.getcwd()
    output_path = f"{cwd}/output_dir"
    pdf_dir = os.path.join(cwd, 'Docs')
    output_dir = os.path.join(output_path, 'extracted_text')
    os.makedirs(output_dir, exist_ok=True)
    embedding_file_path = os.path.join(os.path.expanduser("~"), "Documents", "embeddings")

    
    return pdf_dir, output_dir, embedding_file_path

def get_cwd():
    cwd = os.getcwd()
    input_directory = os.path.join(cwd, 'input')
    
    # List all files in the input directory
    try:
        files = os.listdir(input_directory)
    except PermissionError:
        raise PermissionError(f"Permission denied: Cannot access the directory {input_directory}")
    except FileNotFoundError:
        raise FileNotFoundError(f"The 'input' directory does not exist in {cwd}")
    
    # Find the first CSV file
    csv_files = [f for f in files if f.endswith('.csv')]
    if not csv_files:
        raise FileNotFoundError("No CSV file found in the input directory")
    
    # Return the path of the first CSV file
    return os.path.join(input_directory, csv_files[0])
