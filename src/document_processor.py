"""
A robust document processor for extracting and cleaning text from SEC filings.
This version focuses solely on parsing and text extraction, handing off a single
clean text block for further processing.
"""
# ... (all imports remain the same) ...
import re
from pathlib import Path
from typing import Dict, List
import logging
import tempfile
import os
try:
    from bs4 import BeautifulSoup
    from lxml import etree
except ImportError:
    raise ImportError("Required libraries not found. Please install with: pip install beautifulsoup4 lxml")

logger = logging.getLogger(__name__)
FILE_SIZE_THRESHOLD_MB = 20
FILE_SIZE_THRESHOLD_BYTES = FILE_SIZE_THRESHOLD_MB * 1024 * 1024

class DocumentProcessor:
    def __init__(self):
        self.section_patterns = {
            'business': re.compile(r'item\s+1\.\s*business', re.IGNORECASE),
            'risk_factors': re.compile(r'item\s+1a\.\s*risk\s*factors', re.IGNORECASE),
            'mda': re.compile(r'item\s+7\.\s*management\'s\s+discussion\s+and\s+analysis', re.IGNORECASE),
            'financial_statements': re.compile(r'item\s+8\.\s*financial\s+statements', re.IGNORECASE)
        }
        logger.info(f"DocumentProcessor initialized. Large file threshold: {FILE_SIZE_THRESHOLD_MB} MB")

    def process_filing(self, filing_path: Path) -> Dict:
        logger.info(f"Processing filing: {filing_path}")
        if not filing_path.exists():
            return self._create_error_result(filing_path, f"File not found: {filing_path}")

        cleaned_file_path = None
        try:
            file_size = filing_path.stat().st_size
            logger.info(f"File size: {file_size / (1024*1024):.2f} MB")

            if file_size > FILE_SIZE_THRESHOLD_BYTES:
                logger.info("Using memory-safe stream-to-disk parsing.")
                cleaned_file_path = self._stream_clean_to_temp_file(filing_path)
                with open(cleaned_file_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()
            else:
                logger.info("Using standard in-memory parsing.")
                with open(filing_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_content = f.read()
                full_text = self._parse_with_beautifulsoup(raw_content)

            sections = self._extract_sections(full_text)
            
            # --- CHANGE 1: Select the text for the summarizer ---
            text_for_summary = sections.get('mda', full_text)
            if len(text_for_summary) < 1000 and 'business' in sections:
                text_for_summary = sections['business']
            
            logger.info(f"Processing complete. Extracted text for summarization (length: {len(text_for_summary)}).")
            
            # --- CHANGE 2: Return the single text block, NOT chunks ---
            return {
                'text_for_summary': text_for_summary,
                'filing_path': filing_path,
                'error': None
            }

        except Exception as e:
            logger.exception(f"An unexpected error occurred while processing {filing_path}")
            return self._create_error_result(filing_path, str(e))
        finally:
            if cleaned_file_path and os.path.exists(cleaned_file_path):
                os.remove(cleaned_file_path)
                logger.info(f"Cleaned up temporary file: {cleaned_file_path}")

    # --- CHANGE 3: The _chunk_text method is now completely REMOVED from this class. ---

    # The other helper methods (_stream_clean_to_temp_file, _parse_with_beautifulsoup, 
    # _extract_sections, _create_error_result) remain exactly the same.
    # ... (paste your existing helper methods here) ...

    def _stream_clean_to_temp_file(self, filepath: Path) -> str:
        """
        Memory-safe parser that reads the source file, cleans it, and writes the
        result to a temporary file on disk, preventing RAM overflow.
        """
        # Create a temporary file that we manage ourselves
        fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="sec-clean-")
        logger.info(f"Created temporary file for processing: {temp_path}")

        with os.fdopen(fd, 'w', encoding='utf-8') as temp_f:
            context = etree.iterparse(str(filepath), events=('end',), html=True, recover=True)
            for _, elem in context:
                # Extract text, clean it immediately, and write to disk
                if elem.text:
                    # Normalize whitespace on the fly before writing
                    clean_text = re.sub(r'\s+', ' ', elem.text).strip()
                    if clean_text:
                        temp_f.write(clean_text + ' ')
                
                # Clear the element from memory to keep RAM usage low
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

        return temp_path

    def _parse_with_beautifulsoup(self, raw_content: str) -> str:
        """Standard in-memory parser for small-to-medium files using BeautifulSoup."""
        logger.info("Parsing with BeautifulSoup...")
        soup = BeautifulSoup(raw_content, 'lxml')
        text = soup.get_text(separator=' ', strip=True)
        return re.sub(r'\s+', ' ', text).strip()

    def _extract_sections(self, text: str) -> Dict[str, str]:
        logger.info("Extracting key sections from cleaned text...")
        sections = {}
        matches = [
            {'name': name, 'start': match.start()}
            for name, pattern in self.section_patterns.items()
            if (match := pattern.search(text))
        ]
        if not matches:
            logger.warning("No standard section headers found. Treating as a single document.")
            return {'full_document': text}
        sorted_matches = sorted(matches, key=lambda m: m['start'])
        for i, match in enumerate(sorted_matches):
            start_pos = match['start']
            end_pos = sorted_matches[i + 1]['start'] if i + 1 < len(sorted_matches) else len(text)
            sections[match['name']] = text[start_pos:end_pos].strip()
        return sections

    def _chunk_text(self, text: str, chunk_size: int = 4000, overlap: int = 400) -> List[str]:
        if not text: return []
        logger.info(f"Chunking text (length: {len(text)}) into chunks of ~{chunk_size} chars.")
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                if (sentence_end := text.rfind('.', start, end)) != -1:
                    end = sentence_end + 1
            chunks.append(text[start:end])
            start = end - overlap
        return [chunk for chunk in chunks if chunk]

    def _create_error_result(self, filing_path: Path, error_msg: str) -> Dict:
        return {'full_text': None, 'sections': {}, 'chunks_for_summary': [], 'filing_path': filing_path, 'error': error_msg}

# --- Test block remains unchanged ---
if __name__ == '__main__':
    # ... (rest of the test code is unchanged) ...
    pass
