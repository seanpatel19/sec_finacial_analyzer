#!/usr/bin/env python3
"""
SEC Financial Report Analyzer
Main entry point for the application

Usage:
    python main.py AAPL                    # Analyze Apple's latest 10-K
    python main.py AAPL --form 10-Q       # Analyze latest 10-Q
    python main.py --ui                    # Launch web interface

Requirements:
    - conda environment: sec_analyzer
    - Ollama installed with model: e.g., llama3, mistral
"""

import argparse
import sys
from pathlib import Path
import logging
import gc
import json
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.data_collector import SECDataCollector
from src.document_processor import DocumentProcessor
from src.llm_interface import LLMInterface
from src.summarizer import FinancialSummarizer
from src.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SECAnalyzer:
    def __init__(self):
        """Initialize the SEC analyzer with all components"""
        logger.info("Initializing SEC Financial Analyzer...")
        
        self.config = Config()
        self.data_collector = SECDataCollector(self.config)
        # --- CHANGE 1: Corrected initialization of DocumentProcessor ---
        # The new DocumentProcessor is streamlined and doesn't have any arguments.
        self.document_processor = DocumentProcessor()
        self.llm = LLMInterface(self.config.MODEL_NAME)
        self.summarizer = FinancialSummarizer(self.llm, batch_size=3)
        
        logger.info("SEC Financial Analyzer initialized successfully!")
    
    def analyze_company(self, ticker: str, form_type: str = "10-K") -> dict:
        """
        Main analysis pipeline
        
        Args:
            ticker: Company ticker symbol (e.g., 'AAPL')
            form_type: SEC form type (e.g., '10-K', '10-Q')
            
        Returns:
            dict: Analysis results including summary and data
        """
        logger.info(f"Starting analysis for {ticker} - {form_type}")
        
        try:
            # Step 1: Download filing
            logger.info("Step 1: Downloading SEC filing...")
            filing_path = self.data_collector.download_latest_filing(ticker, form_type)
            if not filing_path:
                raise Exception(f"Failed to download filing for {ticker}.")
            logger.info(f"Downloaded filing: {filing_path}")
            
            # Step 2: Process document
            logger.info("Step 2: Processing document...")
            processed_data = self.document_processor.process_filing(filing_path)
            
            # --- CHANGE 2: Robust error checking ---
            # Check the 'error' key in the returned dictionary.
            if processed_data.get('error'):
                raise Exception(f"Document processing failed: {processed_data['error']}")
            
            logger.info("Document processed successfully")
            
            # Step 3: Generate summary
            logger.info("Step 3: Generating AI summary...")
            
            # --- CHANGE 3: Updated call to the summarizer ---
            # We now pass the clean list of text chunks ('chunks_for_summary') to the summarizer.
            # The financial_data parameter is removed as the new processor focuses on text.
            # IMPORTANT: You may need to update your FinancialSummarizer class to handle a list of chunks.
            summary_result = self.summarizer.generate_summary(
                text_to_summarize=processed_data['text_for_summary'], 
                ticker=ticker
                form_type=form_type
            )
            
            # Check for summary errors
            if summary_result['status'] == 'error':
                raise Exception(f"Summary generation failed: {summary_result['error']}")
            
            logger.info("Summary generated successfully")
            
            # Step 4: Save results
            logger.info("Step 4: Saving results...")
            self._save_results(ticker, summary_result, processed_data)
            
            result = {
                'ticker': ticker,
                'form_type': form_type,
                'summary': summary_result['summary'],
                'summary_metadata': summary_result,
                # --- CHANGE 4: Removed financial_data from the final result ---
                'filing_path': filing_path,
                'success': True
            }
            
            logger.info(f"Analysis completed successfully for {ticker}")
            
            # Force garbage collection to free memory
            del processed_data, summary_result
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {str(e)}", exc_info=True)
            return {
                'ticker': ticker,
                'form_type': form_type,
                'error': str(e),
                'success': False
            }
    
    def _save_results(self, ticker: str, summary_result: dict, data: dict):
        """Save analysis results to files"""
        output_dir = Path(self.config.OUTPUT_DIR) / ticker
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save summary text
        summary_file = output_dir / f"{ticker}_summary.txt"
        with open(summary_file, "w", encoding='utf-8') as f:
            f.write(summary_result['summary'])
        
        # Save full summary metadata as JSON
        metadata_file = output_dir / f"{ticker}_summary_metadata.json"
        with open(metadata_file, "w", encoding='utf-8') as f:
            json.dump(summary_result, f, indent=2, default=str)
        
        # --- CHANGE 5: Removed saving of financial_data.csv ---
        # This part is no longer needed as we focus on text summarization.
        
        # Save processing info
        # --- CHANGE 6: Updated keys to match new processor output ---
        processing_info = {
            'text_length': len(data.get('full_text', '')),
            'chunks_count': len(data.get('chunks_for_summary', [])),
            'filing_path': str(data.get('filing_path', '')),
            'processing_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        info_file = output_dir / f"{ticker}_processing_info.json"
        with open(info_file, "w", encoding='utf-8') as f:
            json.dump(processing_info, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_dir}")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="SEC Financial Report Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py AAPL                    # Analyze Apple's latest 10-K
    python main.py MSFT --form 10-Q       # Analyze Microsoft's latest 10-Q
    python main.py --ui                    # Launch web interface
        """
    )
    
    parser.add_argument(
        "ticker", 
        nargs='?',
        help="Company ticker symbol (e.g., AAPL, MSFT, GOOGL)"
    )
    parser.add_argument(
        "--form", 
        default="10-K", 
        help="SEC form type (default: 10-K)"
    )
    parser.add_argument(
        "--ui", 
        action="store_true", 
        help="Launch web interface"
    )
    
    args = parser.parse_args()
    
    if args.ui:
        logger.info("Launching web interface...")
        import subprocess
        try:
            # Assumes streamlit_app.py is in a 'ui' subdirectory
            streamlit_app_path = Path(__file__).parent / "ui" / "streamlit_app.py"
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", str(streamlit_app_path)
            ])
        except KeyboardInterrupt:
            logger.info("Web interface closed by user")
    
    elif args.ticker:
        analyzer = SECAnalyzer()
        result = analyzer.analyze_company(args.ticker.upper(), args.form)
        
        if result['success']:
            print("\n" + "="*60)
            print(f"FINANCIAL ANALYSIS - {result['ticker']} ({result['form_type']})")
            print("="*60)
            print(result['summary'])
            print("\n" + "="*60)
            print("Analysis completed successfully!")
            # Use the actual config path for the output directory message
            output_path = Path(analyzer.config.OUTPUT_DIR) / result['ticker']
            print(f"Results saved to: {output_path}")
        else:
            print(f"\n[ERROR] Analysis failed: {result['error']}")
            sys.exit(1)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()