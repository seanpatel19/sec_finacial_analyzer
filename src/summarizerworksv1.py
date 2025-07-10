"""
Financial report summarization using a high-performance, concurrent "Map-Reduce" strategy.
This version processes multiple document chunks in parallel to maximize GPU utilization and speed.
"""

import logging
from typing import Dict, List
import time
from concurrent.futures import ThreadPoolExecutor

from .llm_interface import LLMInterface

logger = logging.getLogger(__name__)

class FinancialSummarizer:
    def __init__(self, llm: LLMInterface, batch_size: int = 3):
        """
        Initializes the Financial Summarizer for high-performance batch processing.

        Args:
            llm: An instance of the LLMInterface class.
            batch_size: The number of chunks to process concurrently. A value of 2-4 is
                        usually optimal for a single GPU.
        """
        self.llm = llm
        self.batch_size = batch_size
        logger.info(f"FinancialSummarizer initialized for concurrent processing with batch size: {self.batch_size}")

    def generate_summary(self, text_to_summarize: str, ticker: str) -> Dict[str, str]:
        """
        Generates a summary using a parallel Map-Reduce strategy.

        Args:
            text_to_summarize: The full, clean text of the document section to be summarized.
            ticker: The company ticker symbol.

        Returns:
            A dictionary containing the final summary and metadata.
        """
        if not text_to_summarize:
            return self._create_error_result("No content to summarize.")

        logger.info(f"Starting Map-Reduce summary for {ticker} on text of length {len(text_to_summarize)}.")
        start_time = time.time()
        
        # --- Create all chunks first. This is safe now as they are just views into the main string.
        chunks = self._create_chunks(text_to_summarize)
        
        # --- MAP PHASE: Summarize all chunks in parallel ---
        logger.info(f"Map Phase: Summarizing {len(chunks)} chunks in parallel with {self.batch_size} concurrent workers...")
        
        # We use a ThreadPoolExecutor to send multiple requests to the LLM at once.
        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            # The map function applies our summarization function to each chunk.
            # It automatically handles the concurrency.
            chunk_summaries = list(executor.map(lambda chunk: self._summarize_single_chunk(chunk, ticker), chunks))
        
        # Filter out any failed summaries
        successful_summaries = [s for s in chunk_summaries if s]
        logger.info(f"Map Phase Complete. Successfully summarized {len(successful_summaries)} chunks.")

        if not successful_summaries:
            return self._create_error_result("Failed to summarize any chunks of the document.")

        # --- REDUCE PHASE: Combine the chunk summaries into a final report ---
        logger.info("Reduce Phase: Combining chunk summaries into a final report...")
        final_summary = self._combine_summaries(successful_summaries, ticker)

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Full Map-Reduce summary finished in {duration:.2f} seconds.")

        return {
            'status': 'success', 'summary': final_summary, 'ticker': ticker,
            'duration_seconds': duration, 'chunks_processed': len(chunks)
        }

    def _create_chunks(self, text: str, chunk_size: int = 12000) -> List[str]:
        """Creates a list of non-overlapping chunks from the text."""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _summarize_single_chunk(self, chunk: str, ticker: str) -> str:
        """Creates a prompt and calls the LLM to summarize one independent chunk."""
        prompt = (
            f"You are a financial analyst. The following is a small, independent section from a larger financial report for the company {ticker}. "
            "Provide a concise summary of this specific section, focusing only on the key points, figures, and strategic insights it contains. "
            "Do not add introductions or conclusions, just summarize the provided text.\n\n"
            f"DOCUMENT SECTION:\n---\n{chunk}\n---\n\n"
            "CONCISE SUMMARY OF THIS SECTION:"
        )
        try:
            summary = self.llm.generate(prompt)
            if "Error:" in summary:
                logger.error(f"LLM failed to summarize a chunk: {summary}")
                return None
            return summary
        except Exception as e:
            logger.error(f"Exception while summarizing a chunk: {e}")
            return None

    def _combine_summaries(self, summaries: List[str], ticker: str) -> str:
        """Takes a list of chunk summaries and asks the LLM to synthesize a final report."""
        # Join the list of summaries with separators for clarity.
        combined_summaries_text = "\n\n---\n\n".join(
            f"Summary of Part {i+1}:\n{summary}" for i, summary in enumerate(summaries)
        )

        prompt = (
            f"You are a lead financial analyst. You have been given a series of concise summaries from sequential parts of a financial report for {ticker}. "
            "Your task is to synthesize these individual summaries into a single, well-structured, and coherent final report. "
            "Identify the main themes, connect the key data points, and present a holistic overview of the company's performance, risks, and outlook based on the provided information. "
            "Do not just list the summaries; create a flowing narrative.\n\n"
            f"INDIVIDUAL SUMMARIES:\n---\n{combined_summaries_text}\n---\n\n"
            "FINAL SYNTHESIZED REPORT:"
        )
        
        # This is the final LLM call
        final_report = self.llm.generate(prompt, max_tokens=2000) # Allow a larger output for the final report
        return final_report

    def _create_error_result(self, error_msg: str) -> Dict[str, str]:
        return {'summary': f"Error: {error_msg}", 'status': 'error', 'error': error_msg}
