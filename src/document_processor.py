"""
Document processing and text extraction from SEC filings
Complete version optimized for very large files (270k+ lines) with streaming processing
"""

import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Generator
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError
import gc
import logging
from contextlib import contextmanager
import mmap

# Import BeautifulSoup - needed for robust HTML processing
try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("BeautifulSoup4 is required. Install with: pip install beautifulsoup4")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, max_file_size_mb: int = 100, use_fast_mode: bool = False):
        """
        Initialize document processor optimized for very large files
        
        Args:
            max_file_size_mb: Maximum file size in MB before using chunked processing
            use_fast_mode: Use fast regex extraction instead of BeautifulSoup
        """
        self.financial_keywords = [
            'revenue', 'net income', 'total assets', 'total liabilities',
            'cash and cash equivalents', 'stockholders equity', 'operating income'
        ]
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.use_fast_mode = use_fast_mode
        
        # Financial patterns for large file search
        self.financial_patterns = {
            'Revenue': re.compile(r'revenue[s]?\s*.*?\$\s*([\d,]+)', re.IGNORECASE),
            'Net Income': re.compile(r'net\s+income\s*.*?\$\s*([\d,]+)', re.IGNORECASE),
            'Total Assets': re.compile(r'total\s+assets\s*.*?\$\s*([\d,]+)', re.IGNORECASE),
            'Cash': re.compile(r'cash\s+and\s+cash\s+equivalents\s*.*?\$\s*([\d,]+)', re.IGNORECASE)
        }
        
        # Patterns for finding key sections
        self.section_patterns = {
            'business': re.compile(r'(?i)(?:ITEM\s+)?1\s*[\.\s]*BUSINESS', re.IGNORECASE),
            'risk_factors': re.compile(r'(?i)(?:ITEM\s+)?1A\s*[\.\s]*RISK\s+FACTORS', re.IGNORECASE),
            'mda': re.compile(r'(?i)(?:ITEM\s+)?7\s*[\.\s]*MANAGEMENT.*?DISCUSSION', re.IGNORECASE),
            'financial_statements': re.compile(r'(?i)(?:ITEM\s+)?8\s*[\.\s]*FINANCIAL\s+STATEMENTS', re.IGNORECASE)
        }
        
        # Precompile cleaning patterns
        self.whitespace_pattern = re.compile(r'\s+')
        self.special_chars_pattern = re.compile(r'[^\w\s.,!?;:()\-]')
        self.long_numbers_pattern = re.compile(r'\b\d{10,}\b')
        
        logger.info(f"DocumentProcessor initialized for large files - Fast mode: {use_fast_mode}")
    
    @contextmanager
    def _memory_mapped_file(self, filepath: Path):
        """Memory-mapped file reading for large files"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    yield mm.read().decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Memory mapping failed, falling back to regular read: {e}")
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                yield f.read()
    
    def process_filing(self, filing_path: Path) -> Dict:
        """Main processing function optimized for large files"""
        logger.info(f"Processing large file: {filing_path}")
        
        file_size = filing_path.stat().st_size
        logger.info(f"File size: {file_size / (1024*1024):.1f} MB")
        
        # For very large files, always use streaming approach
        if file_size > 50 * 1024 * 1024:  # 50MB threshold
            return self._process_very_large_file(filing_path)
        else:
            return self._process_standard_file(filing_path)
    
    def _process_very_large_file(self, filing_path: Path) -> Dict:
        """Process very large files using streaming approach"""
        logger.info("Using streaming processing for very large file")
        
        try:
            # Stream process the file
            key_sections = self._extract_key_sections_streaming(filing_path)
            financial_data = self._extract_financial_data_streaming(filing_path)
            
            # Combine sections into readable text
            combined_text = self._combine_sections(key_sections)
            
            # Clean and chunk the text
            cleaned_text = self._clean_text(combined_text)
            chunks = self._chunk_text(cleaned_text)
            
            return {
                'text': cleaned_text,
                'chunks': chunks,
                'financial_data': pd.DataFrame(financial_data) if financial_data else pd.DataFrame(),
                'filing_path': filing_path,
                'sections_found': list(key_sections.keys())
            }
            
        except Exception as e:
            logger.error(f"Error processing very large file: {e}")
            return self._create_error_result(filing_path, str(e))
    
    def _extract_key_sections_streaming(self, filing_path: Path) -> Dict[str, str]:
        """Extract key sections by streaming through the file"""
        logger.info("Streaming extraction of key sections...")
        
        sections = {}
        current_section = None
        section_content = []
        lines_read = 0
        
        try:
            with open(filing_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    lines_read += 1
                    
                    # Progress logging
                    if lines_read % 50000 == 0:
                        logger.info(f"Processed {lines_read} lines, found {len(sections)} sections")
                    
                    # Check if this line starts a new section
                    new_section = self._identify_section(line)
                    
                    if new_section:
                        # Save previous section if it exists
                        if current_section and section_content:
                            sections[current_section] = self._clean_section_content(section_content)
                        
                        # Start new section
                        current_section = new_section
                        section_content = [line]
                        logger.info(f"Found section: {new_section} at line {lines_read}")
                    
                    elif current_section:
                        # Add to current section
                        section_content.append(line)
                        
                        # Limit section size to prevent memory issues
                        if len(section_content) > 1000:
                            sections[current_section] = self._clean_section_content(section_content)
                            current_section = None
                            section_content = []
                    
                    # Also look for financial tables anywhere in the file
                    if '$' in line and any(keyword in line.lower() for keyword in ['revenue', 'income', 'assets', 'cash']):
                        if 'financial_highlights' not in sections:
                            sections['financial_highlights'] = ''
                        sections['financial_highlights'] += line
                        
                        # Limit financial highlights
                        if len(sections['financial_highlights']) > 10000:
                            sections['financial_highlights'] = sections['financial_highlights'][:10000]
                
                # Save final section
                if current_section and section_content:
                    sections[current_section] = self._clean_section_content(section_content)
                
                logger.info(f"Streaming complete: {lines_read} lines processed, {len(sections)} sections found")
                
        except Exception as e:
            logger.error(f"Error in streaming extraction: {e}")
        
        return sections
    
    def _identify_section(self, line: str) -> str:
        """Identify if a line starts a key section"""
        line_clean = line.strip()
        
        for section_name, pattern in self.section_patterns.items():
            if pattern.search(line_clean):
                return section_name
        
        # Look for other important sections
        if re.search(r'(?i)executive\s+summary', line_clean):
            return 'executive_summary'
        elif re.search(r'(?i)forward[- ]looking\s+statements', line_clean):
            return 'forward_looking'
        elif re.search(r'(?i)business\s+overview', line_clean):
            return 'business_overview'
        
        return None
    
    def _clean_section_content(self, section_lines: List[str]) -> str:
        """Clean and combine section content"""
        # Join lines and remove HTML tags
        content = ' '.join(section_lines)
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove obvious formatting lines
        lines = content.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            if (len(line) > 20 and 
                not re.match(r'^[\d\s\.\-\(\)$,]+$', line) and
                'style=' not in line and
                'font-' not in line):
                clean_lines.append(line)
        
        return ' '.join(clean_lines)
    
    def _extract_financial_data_streaming(self, filing_path: Path) -> List[Dict]:
        """Extract financial data by streaming through the file"""
        logger.info("Streaming extraction of financial data...")
        
        financial_data = []
        lines_read = 0
        
        try:
            with open(filing_path, 'r', encoding='utf-8', errors='ignore') as f:
                buffer = []
                
                for line in f:
                    lines_read += 1
                    buffer.append(line)
                    
                    # Process in chunks to find financial data
                    if len(buffer) >= 100:  # Process every 100 lines
                        chunk_text = ' '.join(buffer)
                        chunk_financial = self._extract_financial_from_chunk(chunk_text)
                        financial_data.extend(chunk_financial)
                        buffer = []
                    
                    # Progress logging
                    if lines_read % 100000 == 0:
                        logger.info(f"Financial scan: {lines_read} lines, {len(financial_data)} items found")
                
                # Process final buffer
                if buffer:
                    chunk_text = ' '.join(buffer)
                    chunk_financial = self._extract_financial_from_chunk(chunk_text)
                    financial_data.extend(chunk_financial)
                
        except Exception as e:
            logger.error(f"Error in financial data streaming: {e}")
        
        # Remove duplicates and return
        unique_financial = self._deduplicate_financial_data(financial_data)
        logger.info(f"Financial data extraction complete: {len(unique_financial)} unique items")
        
        return unique_financial
    
    def _extract_financial_from_chunk(self, chunk_text: str) -> List[Dict]:
        """Extract financial data from a text chunk"""
        financial_data = []
        
        for metric, pattern in self.financial_patterns.items():
            matches = pattern.findall(chunk_text)
            for match in matches:
                try:
                    value = float(match.replace(',', ''))
                    financial_data.append({
                        'Metric': metric,
                        'Value': value,
                        'Source': 'Streaming'
                    })
                except ValueError:
                    continue
        
        return financial_data
    
    def _deduplicate_financial_data(self, financial_data: List[Dict]) -> List[Dict]:
        """Remove duplicate financial data entries"""
        seen = set()
        unique_data = []
        
        for item in financial_data:
            key = (item['Metric'], item['Value'])
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        return unique_data
    
    def _combine_sections(self, sections: Dict[str, str]) -> str:
        """Combine extracted sections into readable text"""
        combined = []
        
        # Add sections in logical order
        section_order = ['business', 'business_overview', 'executive_summary', 'mda', 'risk_factors', 'financial_highlights']
        
        for section in section_order:
            if section in sections:
                combined.append(f"\n=== {section.upper().replace('_', ' ')} ===\n")
                combined.append(sections[section])
                combined.append("\n")
        
        # Add any remaining sections
        for section_name, content in sections.items():
            if section_name not in section_order:
                combined.append(f"\n=== {section_name.upper().replace('_', ' ')} ===\n")
                combined.append(content)
                combined.append("\n")
        
        return ''.join(combined)
    
    def _process_standard_file(self, filing_path: Path) -> Dict:
        """Process smaller files using standard approach"""
        try:
            with open(filing_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return self._process_content(content, filing_path)
            
        except Exception as e:
            logger.error(f"Error processing standard file: {e}")
            return self._create_error_result(filing_path, str(e))
    
    def _process_content(self, content: str, filing_path: Path) -> Dict:
        """Process content using fallback extraction"""
        try:
            # Use simple but effective extraction
            text_content = self._extract_text_simple(content)
            financial_data = self._extract_financial_simple(content)
            
            cleaned_text = self._clean_text(text_content)
            chunks = self._chunk_text(cleaned_text)
            
            return {
                'text': cleaned_text,
                'chunks': chunks,
                'financial_data': pd.DataFrame(financial_data) if financial_data else pd.DataFrame(),
                'filing_path': filing_path
            }
            
        except Exception as e:
            logger.error(f"Error in _process_content: {e}")
            return self._create_error_result(filing_path, str(e))
    
    def _extract_text_simple(self, content: str) -> str:
        """Simple text extraction for fallback"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', content)
        
        # Clean entities
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'&#\d+;', ' ', text)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:50000]  # Limit to 50k chars
    
    def _extract_financial_simple(self, content: str) -> List[Dict]:
        """Simple financial extraction"""
        financial_data = []
        
        # Search in first 200KB
        search_content = content[:200000]
        
        for metric, pattern in self.financial_patterns.items():
            matches = pattern.findall(search_content)
            for match in matches[:3]:  # Take first 3 matches
                try:
                    value = float(match.replace(',', ''))
                    financial_data.append({
                        'Metric': metric,
                        'Value': value,
                        'Source': 'Simple'
                    })
                except ValueError:
                    continue
        
        return financial_data
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = self.whitespace_pattern.sub(' ', text)
        
        # Remove special characters but keep basic punctuation
        text = self.special_chars_pattern.sub('', text)
        
        # Remove very long numbers (likely formatting artifacts)
        text = self.long_numbers_pattern.sub('', text)
        
        return text.strip()
    
    def _chunk_text(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to end at a sentence boundary
            if end < len(text):
                sentence_end = text.rfind('.', start, end)
                if sentence_end != -1:
                    end = sentence_end + 1
            
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks

    def _create_error_result(self, filing_path: Path, error_msg: str) -> Dict:
        """Create error result structure"""
        return {
            'text': f"Error processing file: {error_msg}",
            'chunks': [],
            'financial_data': pd.DataFrame(),
            'filing_path': filing_path,
            'error': error_msg
        }