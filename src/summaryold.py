"""
Financial report summarization using an efficient, in-process, iterative-refine strategy.
This is the final, optimized version for both speed and memory safety.
"""

import logging
from typing import Dict, List
import time

# --- CHANGE BACK: We no longer need subprocess, sys, or Path here ---
# from .config import Config # We don't need this directly anymore either
from .llm_interface import LLMInterface # This is the object we will use

logger = logging.getLogger(__name__)

class FinancialSummarizer:
    # --- CHANGE BACK: Accept the LLMInterface instance during initialization ---
    def __init__(self, llm: LLMInterface):
        self.llm = llm
        logger.info(f"FinancialSummarizer initialized for fast, in-process summarization.")

    def generate_summary(self, text_to_summarize: str, ticker: str) -> Dict[str, str]:
        if not text_to_summarize:
            return self._create_error_result("No content to summarize.")

        logger.info(f"Starting summarization for {ticker} on text of length {len(text_to_summarize)}.")
        start_time = time.time()

        context_summary = ""
        final_summary = "No summary could be generated."

        chunk_size = 12000
        overlap = 1200
        start_index = 0
        chunk_count = 0

        try:
            while start_index < len(text_to_summarize):
                chunk_count += 1
                end_index = start_index + chunk_size
                chunk = text_to_summarize[start_index:end_index]
                
                logger.info(f"Processing chunk {chunk_count}...")
                prompt = self._create_refine_prompt(ticker, chunk, context_summary)
                
                # --- THE MAJOR CHANGE: Call the LLM directly ---
                # This is much faster than starting a new process each time.
                refined_text = self.llm.generate(prompt)
                
                if not refined_text or "Error:" in refined_text:
                    logger.error(f"LLM failed for chunk {chunk_count}: {refined_text}")
                    start_index += (chunk_size - overlap)
                    continue

                context_summary = refined_text
                final_summary = context_summary
                
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