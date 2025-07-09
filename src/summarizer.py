"""
Financial report summarization using LLM with enhanced error handling and flexibility
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path
from llm_interface import LLMInterface

logger = logging.getLogger(__name__)

class FinancialSummarizer:
    def __init__(self, llm: LLMInterface, default_max_tokens: int = 1500):
        """
        Initialize Financial Summarizer
        
        Args:
            llm: LLMInterface instance
            default_max_tokens: Default maximum tokens for generation
        """
        self.llm = llm
        self.default_max_tokens = default_max_tokens
        logger.info("FinancialSummarizer initialized")
    
    def generate_summary(self, text: str, financial_data: pd.DataFrame, 
                        ticker: str, summary_type: str = "comprehensive") -> Dict[str, str]:
        """
        Generate comprehensive financial summary
        
        Args:
            text: Processed filing text
            financial_data: Extracted financial data
            ticker: Company ticker symbol
            summary_type: Type of summary ("comprehensive", "brief", "risks", "financial_only")
            
        Returns:
            Dict containing summary and metadata
        """
        logger.info(f"Generating {summary_type} summary for {ticker}")
        
        # Validate inputs
        if not self._validate_inputs(text, ticker):
            return self._create_error_result("Invalid input data")
        
        try:
            # Create structured prompt based on type
            system_prompt = self._create_system_prompt(summary_type)
            user_prompt = self._create_user_prompt(text, financial_data, ticker, summary_type)
            
            # Determine appropriate token limit
            max_tokens = self._calculate_max_tokens(summary_type)
            
            # Generate summary
            summary = self.llm.generate_with_context(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=max_tokens
            )
            
            # Process and validate output
            if not summary or "Error generating text" in summary:
                logger.error("LLM generation failed")
                return self._create_error_result("LLM generation failed")
            
            return {
                'summary': summary,
                'ticker': ticker,
                'summary_type': summary_type,
                'financial_data_available': not financial_data.empty,
                'text_length': len(text),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error generating summary for {ticker}: {e}")
            return self._create_error_result(f"Summary generation failed: {str(e)}")
    
    def generate_batch_summaries(self, processed_filings: List[Dict], 
                               summary_type: str = "comprehensive") -> List[Dict]:
        """
        Generate summaries for multiple filings
        
        Args:
            processed_filings: List of processed filing data from DocumentProcessor
            summary_type: Type of summary to generate
            
        Returns:
            List of summary results
        """
        logger.info(f"Generating batch summaries for {len(processed_filings)} filings")
        
        results = []
        for i, filing_data in enumerate(processed_filings):
            logger.info(f"Processing filing {i+1}/{len(processed_filings)}")
            
            # Extract ticker from filename if not provided
            ticker = self._extract_ticker_from_path(filing_data.get('filing_path'))
            
            # Generate summary
            result = self.generate_summary(
                text=filing_data.get('text', ''),
                financial_data=filing_data.get('financial_data', pd.DataFrame()),
                ticker=ticker,
                summary_type=summary_type
            )
            
            # Add filing path for reference
            result['filing_path'] = filing_data.get('filing_path')
            results.append(result)
        
        return results
    
    def _validate_inputs(self, text: str, ticker: str) -> bool:
        """Validate input parameters"""
        if not text or not text.strip():
            logger.error("Empty text provided")
            return False
        
        if not ticker or not ticker.strip():
            logger.error("Empty ticker provided")
            return False
        
        if len(text) < 100:
            logger.warning(f"Text is very short ({len(text)} characters)")
        
        return True
    
    def _calculate_max_tokens(self, summary_type: str) -> int:
        """Calculate appropriate token limit based on summary type"""
        token_limits = {
            'brief': 800,
            'comprehensive': 1500,
            'risks': 1000,
            'financial_only': 1200
        }
        return token_limits.get(summary_type, self.default_max_tokens)
    
    def _create_system_prompt(self, summary_type: str) -> str:
        """Create system prompt based on summary type"""
        
        base_prompt = """You are a financial analyst specializing in SEC filing analysis. 
        Your task is to provide clear, accurate, and structured summaries of company financial reports.
        Be objective and base your analysis on the provided data."""
        
        type_specific = {
            'comprehensive': """
        Focus on:
        1. Key financial metrics and trends
        2. Business performance indicators
        3. Risk factors and challenges
        4. Management insights and strategy
        5. Future outlook
        
        Provide your analysis in a structured format with clear sections.""",
            
            'brief': """
        Provide a concise summary focusing on:
        1. Key financial highlights
        2. Most significant business developments
        3. Critical risks
        Keep the analysis brief but comprehensive.""",
            
            'risks': """
        Focus specifically on:
        1. Risk factors mentioned in the filing
        2. Potential challenges and threats
        3. Regulatory and compliance issues
        4. Market and competitive risks
        5. Financial and operational risks""",
            
            'financial_only': """
        Focus exclusively on:
        1. Financial metrics and performance
        2. Revenue and profitability trends
        3. Cash flow and liquidity
        4. Debt levels and financial position
        5. Key ratios and financial health indicators"""
        }
        
        return base_prompt + type_specific.get(summary_type, type_specific['comprehensive'])
    
    def _create_user_prompt(self, text: str, financial_data: pd.DataFrame, 
                           ticker: str, summary_type: str) -> str:
        """Create user prompt with filing data"""
        
        # Prepare financial data summary
        if not financial_data.empty:
            financial_summary = financial_data.to_string(index=False)
        else:
            financial_summary = "No structured financial data extracted."
        
        # Smart text truncation based on summary type
        max_text_length = self._get_max_text_length(summary_type)
        text_excerpt = self._smart_truncate(text, max_text_length)
        
        # Create format instructions based on type
        format_instructions = self._get_format_instructions(summary_type)
        
        prompt = f"""
        Please analyze this SEC filing for {ticker} and provide a {summary_type} summary:

        EXTRACTED FINANCIAL DATA:
        {financial_summary}

        FILING EXCERPT:
        {text_excerpt}

        {format_instructions}
        """
        
        return prompt
    
    def _get_max_text_length(self, summary_type: str) -> int:
        """Get maximum text length based on summary type"""
        lengths = {
            'brief': 4000,
            'comprehensive': 6000,
            'risks': 5000,
            'financial_only': 5000
        }
        return lengths.get(summary_type, 5000)
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Smart truncation that tries to end at sentence boundaries"""
        if len(text) <= max_length:
            return text
        
        # Try to find a sentence ending near the limit
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        
        if last_period > max_length * 0.8:  # If we found a period in the last 20%
            return truncated[:last_period + 1]
        
        return truncated + "..."
    
    def _get_format_instructions(self, summary_type: str) -> str:
        """Get format instructions based on summary type"""
        
        formats = {
            'comprehensive': """
        Please provide your analysis in the following format:

        ## Executive Summary
        [Brief overview of company's financial position]

        ## Key Financial Metrics
        [Revenue, profitability, debt levels, cash position]

        ## Business Performance
        [Growth trends, market position, operational efficiency]

        ## Risk Factors
        [Key risks mentioned in the filing]

        ## Management Commentary
        [Key insights from management discussion]

        ## Outlook
        [Future prospects and strategic direction]""",
            
            'brief': """
        Please provide a concise summary with:
        - Key financial highlights (2-3 points)
        - Major business developments (2-3 points)
        - Critical risks (2-3 points)""",
            
            'risks': """
        Please provide a risk-focused analysis with:
        ## Risk Assessment
        [Overall risk profile]
        
        ## Specific Risk Factors
        [Detailed risk analysis by category]
        
        ## Risk Mitigation
        [How the company addresses these risks]""",
            
            'financial_only': """
        Please provide financial analysis with:
        ## Financial Performance
        [Revenue, profitability, margins]
        
        ## Financial Position
        [Balance sheet strength, liquidity, debt]
        
        ## Cash Flow Analysis
        [Operating, investing, financing cash flows]
        
        ## Financial Health Assessment
        [Overall financial condition and trends]"""
        }
        
        return formats.get(summary_type, formats['comprehensive'])
    
    def _extract_ticker_from_path(self, filing_path) -> str:
        """Extract ticker from filing path if possible"""
        if not filing_path:
            return "UNKNOWN"
        
        try:
            # Assume filename might contain ticker
            filename = Path(filing_path).stem
            # Simple heuristic - look for 3-4 uppercase letters
            import re
            ticker_match = re.search(r'\b[A-Z]{2,5}\b', filename)
            if ticker_match:
                return ticker_match.group()
        except:
            pass
        
        return "UNKNOWN"
    
    def _create_error_result(self, error_msg: str) -> Dict[str, str]:
        """Create standardized error result"""
        return {
            'summary': f"Error: {error_msg}",
            'ticker': 'UNKNOWN',
            'summary_type': 'error',
            'financial_data_available': False,
            'text_length': 0,
            'status': 'error',
            'error': error_msg
        }