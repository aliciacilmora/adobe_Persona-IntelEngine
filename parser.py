import json
import os
import datetime
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import fitz # PyMuPDF, needed for full text extraction

# --- Configuration ---
MODEL_NAME = os.environ.get("MODEL_PATH", "all-MiniLM-L6-v2")
INPUT_DATA_DIR = "/app/data"
CHALLENGE_INPUT_FILE = os.path.join(INPUT_DATA_DIR, "challenge1b_input.json")
OUTPUT_FILE = os.path.join(INPUT_DATA_DIR, "challenge1b_output.json")

# --- Helper Functions ---
def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- Core Classes ---

class DocumentProcessor:
    """
    Handles loading documents, structures, and creating richer semantic chunks.
    """
    def __init__(self, doc_info, base_path):
        self.filename = doc_info['filename']
        self.pdf_path = os.path.join(base_path, self.filename)
        self.json_path = os.path.join(base_path, os.path.splitext(self.filename)[0] + ".json")
        self.structure = self._load_structure()
        self.full_text_by_page = self._extract_full_text()

    def _load_structure(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Structure JSON not found for {self.filename}. Outline will be empty.")
            return {"title": "Unknown Title", "outline": []}

    def _extract_full_text(self):
        """Extracts plain text from each page of the PDF for context gathering."""
        try:
            doc = fitz.open(self.pdf_path)
            return [page.get_text("text") for page in doc]
        except Exception as e:
            print(f"Warning: Could not extract text from {self.filename}. Error: {e}")
            return []

    def get_semantic_chunks(self):
        """
        Creates contextually rich chunks. Each chunk includes a heading
        and the full text content that follows it.
        """
        chunks = []
        
        # --- FIX #1: Add the main document title as the first, most important chunk ---
        title = self.structure.get('title', 'Untitled Document')
        if title:
            # The content for the title chunk is the text of the first page.
            title_content = self.full_text_by_page[0] if self.full_text_by_page else title
            chunks.append({
                "document": self.filename,
                "section_title": title,
                "content": f"{title}. {title_content}", # Provide rich context for the title
                "page_number": 1 # Title is on page 1
            })

        # --- FIX #2: Create richer chunks for the rest of the outline ---
        outline = self.structure.get('outline', [])
        # Sort outline by page to process in order
        sorted_outline = sorted(outline, key=lambda x: x.get('page', 0))

        for i, item in enumerate(sorted_outline):
            page_idx = item.get('page', 1) - 1
            if page_idx < 0 or page_idx >= len(self.full_text_by_page):
                continue

            start_text = item.get('text', '')
            page_content = self.full_text_by_page[page_idx]
            
            # Find the content under this heading.
            # A simple way is to find the text of the heading and take a snippet after it.
            # A more robust way would use coordinates from 1A, but this is a good start.
            try:
                start_index = page_content.index(start_text)
                # Take up to 500 characters after the heading for context
                content_snippet = page_content[start_index : start_index + 500]
            except ValueError:
                content_snippet = start_text # Fallback to just the heading text
            
            chunks.append({
                "document": self.filename,
                "section_title": start_text,
                "content": content_snippet,
                "page_number": item.get('page', 1)
            })
            
        return chunks

class PersonaIntelEngine:
    """
    The main engine that drives the persona-based analysis.
    """
    def __init__(self, model_name):
        print(f"Loading embedding model from path: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Model loaded successfully.")
    
    def run(self, input_data):
        persona = input_data['persona']['role']
        job_to_be_done = input_data['job_to_be_done']['task']
        compound_query = f"As a {persona}, I need to {job_to_be_done}"
        print(f"Compound Query: {compound_query}")

        all_chunks = []
        doc_processors = [DocumentProcessor(doc, INPUT_DATA_DIR) for doc in input_data['documents']]
        for processor in doc_processors:
            all_chunks.extend(processor.get_semantic_chunks())

        if not all_chunks:
            print("No processable chunks found in any document.")
            self._write_empty_output(input_data)
            return

        print(f"Embedding {len(all_chunks)} chunks...")
        query_embedding = self.model.encode([compound_query])
        chunk_embeddings = self.model.encode([chunk['content'] for chunk in all_chunks])
        print("Embedding complete.")

        similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
        
        for i, chunk in enumerate(all_chunks):
            chunk['relevance_score'] = similarities[i]

        # --- FIX #3: Prevent duplicate sections in the output ---
        # Sometimes, the title and the first H1 are very similar. We only want the best one.
        unique_ranked_chunks = []
        seen_titles = set()
        
        # Sort chunks by relevance score in descending order
        ranked_chunks = sorted(all_chunks, key=lambda x: x['relevance_score'], reverse=True)

        for chunk in ranked_chunks:
            # Normalize title for uniqueness check
            normalized_title = chunk['section_title'].strip().lower()
            if normalized_title not in seen_titles:
                unique_ranked_chunks.append(chunk)
                seen_titles.add(normalized_title)
        
        self._generate_output(input_data, unique_ranked_chunks)

    def _generate_output(self, input_data, ranked_chunks):
        metadata = {
            "input_documents": [doc['filename'] for doc in input_data['documents']],
            "persona": input_data['persona']['role'],
            "job_to_be_done": input_data['job_to_be_done']['task'],
            "processing_timestamp": datetime.datetime.now().isoformat()
        }

        extracted_sections = []
        for i, chunk in enumerate(ranked_chunks[:5]): # Take top 5 unique sections
            extracted_sections.append({
                "document": chunk['document'],
                "section_title": chunk['section_title'],
                "importance_rank": i + 1,
                "page_number": chunk['page_number']
            })
            
        subsection_analysis = []
        for chunk in ranked_chunks[:5]:
             # For refined_text, we now use the richer 'content' from our chunk
             subsection_analysis.append({
                "document": chunk['document'],
                "refined_text": clean_text(chunk['content']),
                "page_number": chunk['page_number']
            })

        final_output = {
            "metadata": metadata,
            "extracted_sections": extracted_sections,
            "subsection_analysis": subsection_analysis
        }

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=4, ensure_ascii=False)
        print(f"Successfully generated output at {OUTPUT_FILE}")

    def _write_empty_output(self, input_data):
        metadata = { "input_documents": [doc['filename'] for doc in input_data['documents']], "persona": input_data['persona']['role'], "job_to_be_done": input_data['job_to_be_done']['task'], "processing_timestamp": datetime.datetime.now().isoformat() }
        final_output = {"metadata": metadata, "extracted_sections": [], "subsection_analysis": []}
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: json.dump(final_output, f, indent=4, ensure_ascii=False)


# --- Main Execution Block ---
if __name__ == "__main__":
    if not os.path.exists(CHALLENGE_INPUT_FILE):
        print(f"Error: Main input file not found at {CHALLENGE_INPUT_FILE}")
    else:
        with open(CHALLENGE_INPUT_FILE, 'r', encoding='utf-8') as f:
            challenge_data = json.load(f)
        engine = PersonaIntelEngine(MODEL_NAME)
        engine.run(challenge_data)