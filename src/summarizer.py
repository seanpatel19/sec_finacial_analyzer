"""
Financial report summarization using a process-isolated, iterative-refine strategy.
This version performs its own chunking on the fly to avoid creating large lists in memory.
"""
# ... (keep imports the same) ...
import logging
from typing import Dict, List
import time
import subprocess
import sys
from pathlib import Path
from .config import Config

logger = logging.getLogger(__name__)

class FinancialSummarizer:
    def __init__(self):
        self.config = Config()
        self.caller_script_path = Path(__file__).parent / "llm_caller.py"
        logger.info(f"FinancialSummarizer initialized for on-the-fly chunking and process-isolated LLM calls.")

    # --- CHANGE 1: Update the function signature ---
    def generate_summary(self, text_to_summarize: str, ticker: str) -> Dict[str, str]:
        if not text_to_summarize:
            return self._create_error_result("No content to summarize.")

        logger.info(f"Starting summarization for {ticker} on text of length {len(text_to_summarize)}.")
        start_time = time.time()

        context_summary = ""
        final_summary = "No summary could be generated."

        # --- CHANGE 2: On-the-fly chunking loop ---
        chunk_size = 4000
        overlap = 400
        start_index = 0
        chunk_count = 0

        try:
            while start_index < len(text_to_summarize):
                chunk_count += 1
                end_index = start_index + chunk_size
                
                # Get the current chunk by slicing the main text
                chunk = text_to_summarize[start_index:end_index]
                
                logger.info(f"Processing chunk {chunk_count}...")
                prompt = self._create_refine_prompt(ticker, chunk, context_summary)
                
                try:
                    command = [sys.executable, str(self.caller_script_path), self.config.MODEL_NAME, prompt]
                    result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
                    refined_text = result.stdout.strip()
                except subprocess.CalledProcessError as e:
                    logger.error(f"LLM caller script failed for chunk {chunk_count}. Error: {e.stderr.strip()}")
                    start_index += (chunk_size - overlap) # Move to the next chunk even if this one failed
                    continue

                if refined_text:
                    context_summary = refined_text
                    final_summary = context_summary
                
                # Move the window for the next chunk
                start_index += (chunk_size - overlap)

            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"Summarization finished in {duration:.2f} seconds.")

            return {
                'status': 'success', 'summary': final_summary, 'ticker': ticker,
                'duration_seconds': duration, 'chunks_processed': chunk_count
            }
        
        except Exception as e:
            logger.exception(f"A critical error occurred during summary generation for {ticker}")
            return self._create_error_result(f"Summary generation failed: {str(e)}")

    # _create_refine_prompt and _create_error_result remain unchanged
    # ... (paste your existing helper methods here) ...

    def _create_refine_prompt(self, ticker: str, new_chunk: str, existing_summary: str) -> str:
        # This function remains unchanged
        if not existing_summary:
            return (
                f"You are a meticulous financial analyst. Your task is to summarize a section of a financial report for the company {ticker}. "
                "This is the first part of the document. Focus on the key points, financial figures, and strategic insights.\n\n"
                f"DOCUMENT SECTION:\n---\n{new_chunk}\n---\n\n"
                "CONCISE SUMMARY OF THIS SECTION:"
            )
        else:
            return (
                "You are a meticulous financial analyst. You have an existing summary of the previous parts of a financial report. "
                "Your task is to refine and enrich this summary with new, relevant information from the next section of the document. "
                "Integrate the new key points into the existing narrative. Do not simply list new facts. "
                "If the new section is boilerplate or doesn't add value, simply return the 'EXISTING SUMMARY' without changes.\n\n"
                f"EXISTING SUMMARY:\n---\n{existing_summary}\n---\n\n"
                f"NEW DOCUMENT SECTION:\n---\n{new_chunk}\n---\n\n"
                "IMPROVED AND REFINED SUMMARY:"
            )

    def _create_error_result(self, error_msg: str) -> Dict[str, str]:
        # This function remains unchanged
        return {'summary': f"Error: {error_msg}", 'status': 'error', 'error': error_msg}