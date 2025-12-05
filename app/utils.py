"""
Utility functions for extracting text from various document formats
"""
import os
from PyPDF2 import PdfReader
from docx import Document

def extract_text_from_pdf(file_path):
    """
    Extract text from PDF file
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text as string
    """
    try:
        reader = PdfReader(file_path)
        text = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        
        return '\n\n'.join(text)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(file_path):
    """
    Extract text from DOCX file
    
    Args:
        file_path: Path to DOCX file
        
    Returns:
        Extracted text as string
    """
    try:
        doc = Document(file_path)
        text = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        
        return '\n\n'.join(text)
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_txt(file_path):
    """
    Extract text from TXT file
    
    Args:
        file_path: Path to TXT file
        
    Returns:
        Extracted text as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT file: {e}")
        return ""

def extract_text_from_file(file_path):
    """
    Extract text from file based on extension
    
    Args:
        file_path: Path to file
        
    Returns:
        Extracted text as string
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext in ['.txt', '.text']:
        return extract_text_from_txt(file_path)
    else:
        print(f"Unsupported file type: {ext}")
        return ""
