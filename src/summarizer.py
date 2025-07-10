"""
Financial report summarization using a stable, sequential, and resumable strategy.
This is the definitive architecture for long-running, local LLM tasks, prioritizing
reliability and the ability to resume over raw speed.
"""

import logging
from typing import Dict, List
import time
import json
from pathlib import Path

from .llm_interface import LLMInterface
from .config import Config

logger = logging.getLogger(__name__)

class FinancialSummarizer:
    def __init__(self, llm: LLMInterface):
        self.llm = llm
        self.config = Config()
        logger.info("FinancialSummarizer initialized for stable, resumable processing.")

    def generate_summary(self, text_to_summarize: str, ticker: str, form_type: str) -> Dict[str, str]:
        """
        Generates a summary using a sequential process that saves progress after each chunk.
        """
        if not text_to_summarize:
            return self._create_error_result("No content to summarize.")

        logger.info(f"Starting resumable summary for {ticker} ({form_type})...")
        start_time = time.time()
        
        # --- RESUMPTION LOGIC: Define a cache file path for this specific document ---
        cache_dir = Path(self.config.OUTPUT_DIR) / ticker / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{form_type}_chunk_summaries.json"
        
        # --- Load existing summaries if the cache file exists ---
        chunk_summaries = self._load_cache(cache_file)
        
        chunks = self._create_chunks(text_to_summarize)
        
        # --- SEQUENTIAL PROCESSING LOOP ---
        for i, chunk in enumerate(chunks):
            # --- RESUMPTION CHECK ---
            if i < len(chunk_summaries):
                logger.info(f"Skipping chunk {i + 1}/{len(chunks)} (already processed).")
                continue

            logger.info(f"Processing chunk {i + 1}/{len(chunks)}...")
            prompt = self._create_chunk_prompt(chunk, ticker)
            
            summary = self.llm.generate(prompt)
            if "Error:" in summary:
                logger.error(f"LLM failed on chunk {i + 1}. Aborting run. Re-run to resume. Error: {summary}")
                return self._create_error_result(f"LLM failed on chunk {i+1}")

            # --- SAVE PROGRESS IMMEDIATELY ---
            chunk_summaries.append(summary)
            self._save_cache(cache_file, chunk_summaries)
            logger.info(f"Saved progress for chunk {i + 1}.")

        logger.info("All chunks have been summarized. Combining into a final report...")
        final_summary = self._combine_summaries(chunk_summaries, ticker)

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Full summary generation finished in {duration:.2f} seconds.")

        # Clean up the cache file after successful completion
        # cache_file.unlink()

        return {
            'status': 'success', 'summary': final_summary, 'ticker': ticker,
            'duration_seconds': duration, 'chunks_processed': len(chunks)
        }

    def _load_cache(self, cache_file: Path) -> List[str]:
        """Loads previously summarized chunks from a JSON file."""
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
                logger.info(f"Resuming analysis. Found {len(summaries)} previously completed chunks.")
                return summaries
        return []

    def _save_cache(self, cache_file: Path, summaries: List[str]):
        """Saves the list of chunk summaries to a JSON file."""
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, indent=2)

    def _create_chunks(self, text: str, chunk_size: int = 12000) -> List[str]:
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _create_chunk_prompt(self, chunk: str, ticker: str) -> str:
        return (
            f"You are a financial analyst. The following is a small, independent section from a larger financial report for the company {ticker}. "
            "Provide a concise summary of this specific section, focusing only on the key points, figures, and strategic insights it contains. "
            "Do not add introductions or conclusions, just summarize the provided text.\n\n"
            f"DOCUMENT SECTION:\n---\n{chunk}\n---\n\n"
            "CONCISE SUMMARY OF THIS SECTION:"
        )

    def _combine_summaries(self, summaries: List[str], ticker: str) -> str:
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
        final_report = self.llm.generate(prompt, max_tokens=2000)
        return final_report

    def _create_error_result(self, error_msg: str) -> Dict[str, str]:
        return {'summary': f"Error: {error_msg}", 'status': 'error', 'error': error_msg}
