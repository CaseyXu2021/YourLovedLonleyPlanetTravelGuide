"""
PDF to Knowledge Base Generator
Convert PDF files to pkl knowledge bases for semantic search
"""

import os
import pickle
import sys
from pathlib import Path
from typing import List, Dict, Optional
import re

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

from sentence_transformers import SentenceTransformer
import numpy as np


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    if not HAS_PYPDF2:
        raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2")
    
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""
    
    return text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
    """
    Split text into overlapping chunks and clean them.
    
    Args:
        text: Full text to chunk
        chunk_size: Number of characters per chunk
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of chunk dictionaries with metadata
    """
    # Clean text
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'\n+', ' ', text)  # Remove newlines
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Try to break at sentence boundary if not at end
        if end < len(text):
            last_period = text.rfind('.', start, end)
            if last_period > start + chunk_size * 0.5:
                end = last_period + 1
        
        chunk_text = text[start:end].strip()
        
        if chunk_text:  # Only add non-empty chunks
            chunks.append({
                "text": chunk_text,
                "start_char": start,
                "end_char": end
            })
        
        start = end - overlap if end < len(text) else end
    
    return chunks


def generate_embeddings(
    texts: List[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> np.ndarray:
    """Generate embeddings for a list of texts."""
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    
    return embeddings


def create_knowledge_base(pdf_path: str, country_name: str) -> Dict:
    """
    Create a knowledge base from a PDF file.
    
    Args:
        pdf_path: Path to PDF file
        country_name: Name of the country/destination
    
    Returns:
        Knowledge base dictionary with chunks and embeddings
    """
    print(f"\n{'='*60}")
    print(f"Processing: {country_name}")
    print(f"{'='*60}")
    
    # Extract text from PDF
    print(f"📄 Extracting text from {pdf_path}...")
    full_text = extract_text_from_pdf(pdf_path)
    
    if not full_text:
        print(f"❌ No text extracted from {pdf_path}")
        return None
    
    print(f"✅ Extracted {len(full_text)} characters")
    
    # Chunk text
    print(f"📝 Chunking text...")
    chunks = chunk_text(full_text, chunk_size=500, overlap=50)
    print(f"✅ Created {len(chunks)} chunks")
    
    # Extract chunk texts for embedding
    chunk_texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings
    embeddings = generate_embeddings(chunk_texts)
    
    # Create knowledge base
    knowledge_base = {
        "chunks": chunks,
        "embeddings": embeddings,
        "country_name": country_name,
        "total_characters": len(full_text),
        "chunk_count": len(chunks)
    }
    
    return knowledge_base


def save_knowledge_base(kb: Dict, output_path: str) -> bool:
    """Save knowledge base to pickle file."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            pickle.dump(kb, f)
        print(f"✅ Saved to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving {output_path}: {e}")
        return False


def process_pdf_files(pdf_files: List[tuple]) -> None:
    """
    Process multiple PDF files and generate knowledge bases.
    
    Args:
        pdf_files: List of tuples (pdf_path, country_name)
    """
    knowledge_bases_dir = Path(__file__).resolve().parent / "knowledge_bases"
    
    results = []
    
    for pdf_path, country_name in pdf_files:
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            print(f"❌ File not found: {pdf_path}")
            results.append((country_name, False, f"File not found"))
            continue
        
        # Create knowledge base
        kb = create_knowledge_base(str(pdf_path), country_name)
        if not kb:
            results.append((country_name, False, "Failed to extract text"))
            continue
        
        # Save knowledge base
        output_path = knowledge_bases_dir / f"{country_name}.pkl"
        if save_knowledge_base(kb, str(output_path)):
            results.append((country_name, True, f"{len(kb['chunks'])} chunks"))
        else:
            results.append((country_name, False, "Failed to save"))
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 PROCESSING SUMMARY")
    print(f"{'='*60}")
    
    for country_name, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {country_name:20} - {message}")
    
    print(f"\n✨ Processing complete!")


if __name__ == "__main__":
    # List of PDF files to process
    pdf_files = [
        (r"C:\Users\Casey\Downloads\New Book\Argentina.pdf", "Argentina"),
        (r"C:\Users\Casey\Downloads\New Book\Japan.pdf", "Japan"),
        (r"C:\Users\Casey\Downloads\New Book\Netherlands.pdf", "Netherlands"),
        (r"C:\Users\Casey\Downloads\New Book\Sicily.pdf", "Sicily"),
    ]
    
    # Check if PyPDF2 is installed
    if not HAS_PYPDF2:
        print("Installing PyPDF2...")
        os.system("pip install PyPDF2 -q")
    
    # Process all files
    process_pdf_files(pdf_files)
