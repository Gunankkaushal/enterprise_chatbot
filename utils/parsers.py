import fitz
import re
from collections import Counter
from typing import List, Dict, Any, Tuple
from docx import Document as DocxDocument

from .helpers import clean_text_pipeline, normalize_whitespace

def remove_headers_footers(pages_text: List[str]) -> Tuple[List[str], str]:
    def normalize_line_for_comparison(line: str) -> str:
        line_no_digits = re.sub(r'\d+', '', line)
        return line_no_digits.lower().strip()

    header_weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
    footer_weights = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    
    potential_headers = []
    potential_footers = []
    
    for text in pages_text:
        lines = [line for line in text.split('\n') if line.strip()]
        if not lines:
            continue
            
        for i in range(min(len(lines), len(header_weights))):
            normalized_line = normalize_line_for_comparison(lines[i])
            potential_headers.append((normalized_line, i))
            
        for i in range(min(len(lines), len(footer_weights))):
            line_index_from_bottom = len(lines) - 1 - i
            normalized_line = normalize_line_for_comparison(lines[line_index_from_bottom])
            potential_footers.append((normalized_line, i))

    header_counts = Counter(potential_headers)
    footer_counts = Counter(potential_footers)

    base_min_occurrence = int(len(pages_text) * 0.40)
    if base_min_occurrence < 2 and len(pages_text) > 1:
        base_min_occurrence = 2

    common_headers = {
        line for (line, pos_index), count in header_counts.items()
        if count >= (base_min_occurrence / header_weights[pos_index])
    }

    common_footers = {
        line for (line, pos_index), count in footer_counts.items()
        if count >= (base_min_occurrence / footer_weights[pos_index])
    }

    first_header_instance = []
    cleaned_pages = []
    is_first_header_captured = False

    for text in pages_text:
        lines = text.split('\n')
        header_end_index = 0
        current_header_lines = []
        
        for i, line in enumerate(lines):
            normalized_line = normalize_line_for_comparison(line)
            if line.strip() and normalized_line in common_headers:
                current_header_lines.append(line)
            elif line.strip() and normalized_line not in common_headers:
                header_end_index = i
                break
        
        if not is_first_header_captured and current_header_lines:
            first_header_instance = current_header_lines
            is_first_header_captured = True

        footer_start_index = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            normalized_line = normalize_line_for_comparison(lines[i])
            if line.strip() and normalized_line not in common_footers:
                footer_start_index = i + 1
                break
        
        if header_end_index < footer_start_index:
            cleaned_page_lines = lines[header_end_index:footer_start_index]
            cleaned_pages.append('\n'.join(cleaned_page_lines))
        else:
            cleaned_pages.append(text)
        
    doc_context = '\n'.join(first_header_instance)
    return cleaned_pages, doc_context

def extract_from_pdf(file_path: str) -> Dict[str, Any]:
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Error opening PDF file: {e}")
    
    raw_pages_text = [page.get_text("text") for page in doc]
    structurally_cleaned_pages, doc_context = remove_headers_footers(raw_pages_text)

    final_pages_data = []
    for i, page_text in enumerate(structurally_cleaned_pages):
        processed_text = clean_text_pipeline(page_text)
        normalized_page_text = normalize_whitespace(processed_text)
        
        if normalized_page_text:
            final_pages_data.append({
                "page_number": i + 1,
                "text": normalized_page_text
            })
    
    return {
        "doc_context": clean_text_pipeline(doc_context),
        "pages": final_pages_data
    }

def extract_from_docx(file_path: str) -> Dict[str, Any]:
    doc = DocxDocument(file_path)
    raw_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    processed_text = clean_text_pipeline(raw_text)
    normalized_text = normalize_whitespace(processed_text)
    
    return {
        "doc_context": "",
        "pages": [{"page_number": 1, "text": normalized_text}] if normalized_text else []
    }

def extract_and_clean_document(file_path: str, extension: str) -> Dict[str, Any]:
    if extension == ".pdf":
        return extract_from_pdf(file_path)
    elif extension == ".docx":
        return extract_from_docx(file_path)
    raise ValueError("Unsupported file extension")