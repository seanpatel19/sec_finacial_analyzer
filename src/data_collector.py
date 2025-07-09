"""
SEC EDGAR data collection and download functionality
Handles downloading SEC filings from the EDGAR database
"""

import requests
import time
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class SECDataCollector:
    """Handles SEC EDGAR data collection and filing downloads"""
    
    def __init__(self, config):
        """
        Initialize SEC data collector
        
        Args:
            config: Configuration object with SEC settings
        """
        self.config = config
        self.session = requests.Session()
        
        # Validate required config attributes
        required_attrs = ['USER_AGENT', 'SEC_BASE_URL', 'REQUEST_DELAY', 'RAW_FILINGS_DIR']
        for attr in required_attrs:
            if not hasattr(config, attr):
                raise ValueError(f"Config missing required attribute: {attr}")
        
        # Ensure RAW_FILINGS_DIR exists
        self.config.RAW_FILINGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create cache directory for ticker mappings
        self.cache_dir = Path(config.RAW_FILINGS_DIR).parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ticker_cache_file = self.cache_dir / "company_tickers.json"
        
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # Load ticker-CIK mapping
        self.ticker_cik_mapping = self._load_ticker_mapping()
        
        logger.info(f"SEC Data Collector initialized with {len(self.ticker_cik_mapping)} ticker mappings")
    
    def _load_ticker_mapping(self) -> Dict[str, str]:
        """
        Load ticker to CIK mapping from SEC's official JSON files
        """
        # Check if cached file exists and is recent (less than 24 hours old)
        if (self.ticker_cache_file.exists() and 
            time.time() - self.ticker_cache_file.stat().st_mtime < 24 * 3600):
            logger.info("Loading ticker mapping from cache")
            try:
                with open(self.ticker_cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        
        # Download fresh mapping
        return self._download_ticker_mapping()
    
    def _download_ticker_mapping(self) -> Dict[str, str]:
        """
        Download ticker to CIK mapping from SEC's official JSON files
        """
        logger.info("Downloading ticker to CIK mapping from SEC...")
        
        # Try both ticker endpoints
        endpoints = [
            "https://www.sec.gov/files/company_tickers.json",
            "https://www.sec.gov/files/company_tickers_exchange.json"
        ]
        
        for url in endpoints:
            try:
                logger.info(f"Trying endpoint: {url}")
                time.sleep(self.config.REQUEST_DELAY)
                
                response = self.session.get(url)
                response.raise_for_status()
                
                data = response.json()
                mapping = self._parse_ticker_data(data)
                
                if mapping:
                    logger.info(f"Successfully downloaded {len(mapping)} ticker mappings")
                    self._save_ticker_mapping(mapping)
                    return mapping
                    
            except Exception as e:
                logger.warning(f"Failed to download from {url}: {e}")
                continue
        
        logger.error("All ticker endpoints failed")
        return {}
    
    def _parse_ticker_data(self, data: dict) -> Dict[str, str]:
        """
        Parse ticker data from SEC JSON response
        """
        mapping = {}
        
        try:
            # Handle different response formats
            if isinstance(data, dict):
                # Check if it's the indexed format: {"0": {"ticker": "AAPL", "cik_str": 320193}, ...}
                for key, entry in data.items():
                    if isinstance(entry, dict) and 'ticker' in entry:
                        ticker = entry['ticker']
                        cik = str(entry.get('cik_str', entry.get('cik', ''))).zfill(10)
                        if ticker and cik != '0000000000':
                            mapping[ticker.upper()] = cik
                            
                # Also check for direct array format in 'data' key
                if 'data' in data and isinstance(data['data'], list):
                    for entry in data['data']:
                        if isinstance(entry, list) and len(entry) >= 2:
                            # Format: [ticker, cik, name] or similar
                            ticker = entry[0] if isinstance(entry[0], str) else entry[1]
                            cik_val = entry[1] if isinstance(entry[1], int) else entry[0]
                            cik = str(cik_val).zfill(10)
                            if ticker and cik != '0000000000':
                                mapping[ticker.upper()] = cik
            
            logger.info(f"Parsed {len(mapping)} ticker-CIK mappings")
            return mapping
            
        except Exception as e:
            logger.error(f"Error parsing ticker data: {e}")
            return {}
    
    def _save_ticker_mapping(self, mapping: Dict[str, str]):
        """
        Save ticker mapping to cache file
        """
        try:
            with open(self.ticker_cache_file, 'w') as f:
                json.dump(mapping, f, indent=2)
            logger.info(f"Saved ticker mapping to {self.ticker_cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save ticker mapping: {e}")
    
    def get_company_cik(self, ticker: str) -> str:
        """
        Get CIK (Central Index Key) number for a company ticker
        
        Args:
            ticker: Company ticker symbol (e.g., 'AAPL')
            
        Returns:
            str: 10-digit CIK number
            
        Raises:
            ValueError: If ticker is not found
        """
        logger.info(f"Looking up CIK for ticker: {ticker}")
        
        ticker_upper = ticker.upper()
        
        # Check our mapping
        if ticker_upper in self.ticker_cik_mapping:
            cik = self.ticker_cik_mapping[ticker_upper]
            logger.info(f"Found CIK {cik} for ticker {ticker}")
            return cik
        
        # If not found, try to refresh the mapping
        logger.info("Ticker not found in cache, refreshing mapping...")
        self.ticker_cik_mapping = self._download_ticker_mapping()
        
        if ticker_upper in self.ticker_cik_mapping:
            cik = self.ticker_cik_mapping[ticker_upper]
            logger.info(f"Found CIK {cik} for ticker {ticker} after refresh")
            return cik
        
        # Still not found
        raise ValueError(f"Ticker {ticker} not found in SEC database. "
                        f"Please verify the ticker symbol is correct.")
    
    def add_ticker_mapping(self, ticker: str, cik: str):
        """
        Manually add a ticker to CIK mapping
        
        Args:
            ticker: Company ticker symbol
            cik: 10-digit CIK number
        """
        cik_formatted = str(cik).zfill(10)
        self.ticker_cik_mapping[ticker.upper()] = cik_formatted
        self._save_ticker_mapping(self.ticker_cik_mapping)
        logger.info(f"Added mapping: {ticker} -> {cik_formatted}")
    
    def get_company_filings(self, cik: str, form_type: str = "10-K") -> List[Dict]:
        """
        Get list of company filings for a specific form type
        
        Args:
            cik: Company CIK number
            form_type: SEC form type (e.g., '10-K', '10-Q')
            
        Returns:
            List[Dict]: List of filing information, sorted by date (newest first)
        """
        logger.info(f"Fetching {form_type} filings for CIK {cik}")
        
        # Ensure CIK is properly formatted
        cik_formatted = str(cik).zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_formatted}.json"
        
        try:
            time.sleep(self.config.REQUEST_DELAY)
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Validate response structure
            if 'filings' not in data or 'recent' not in data['filings']:
                raise ValueError(f"Invalid response structure for CIK {cik}")
            
            filings = data['filings']['recent']
            
            # Validate required fields exist
            required_fields = ['form', 'accessionNumber', 'filingDate']
            for field in required_fields:
                if field not in filings:
                    raise ValueError(f"Missing required field '{field}' in filings data")
            
            # Filter by form type
            filtered_filings = []
            for i, form in enumerate(filings['form']):
                if form == form_type:
                    # Add bounds checking
                    if i >= len(filings['accessionNumber']) or i >= len(filings['filingDate']):
                        logger.warning(f"Index {i} out of bounds for filing data")
                        continue
                        
                    filtered_filings.append({
                        'accessionNumber': filings['accessionNumber'][i],
                        'filingDate': filings['filingDate'][i],
                        'reportDate': filings.get('reportDate', [None] * len(filings['form']))[i],
                        'form': form,
                        'fileNumber': filings.get('fileNumber', [None] * len(filings['form']))[i]
                    })
            
            # Sort by filing date (newest first)
            filtered_filings.sort(key=lambda x: x['filingDate'], reverse=True)
            
            logger.info(f"Found {len(filtered_filings)} {form_type} filings")
            return filtered_filings
            
        except requests.RequestException as e:
            logger.error(f"Error fetching filings: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise
    
    def download_filing(self, cik: str, accession_number: str) -> Path:
        """
        Download a specific filing using the correct SEC path structure
        
        Args:
            cik: Company CIK number
            accession_number: SEC accession number (e.g., '0001193125-15-118890')
            
        Returns:
            Path: Path to downloaded file
        """
        logger.info(f"Downloading filing {accession_number} for CIK {cik}")
        
        # Ensure CIK is properly formatted
        cik_formatted = str(cik).zfill(10)
        cik_int = int(cik_formatted)  # For URL (no leading zeros)
        
        # Construct filing URL using the path structure from documentation
        # Format: /Archives/edgar/data/{CIK}/{accession_number}.txt
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_number}.txt"
        
        try:
            time.sleep(self.config.REQUEST_DELAY)
            response = self.session.get(filing_url)
            response.raise_for_status()
            
            # Save to file
            filename = f"{cik_formatted}_{accession_number}.txt"
            filepath = self.config.RAW_FILINGS_DIR / filename
            
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Filing saved to {filepath}")
            return filepath
            
        except requests.RequestException as e:
            logger.error(f"Error downloading filing from {filing_url}: {e}")
            raise
        except IOError as e:
            logger.error(f"Error writing file: {e}")
            raise
    
    def download_latest_filing(self, ticker: str, form_type: str = "10-K") -> Path:
        """
        Download the latest filing for a company
        
        Args:
            ticker: Company ticker symbol
            form_type: SEC form type
            
        Returns:
            Path: Path to downloaded file
        """
        logger.info(f"Downloading latest {form_type} for {ticker}")
        
        try:
            cik = self.get_company_cik(ticker)
            filings = self.get_company_filings(cik, form_type)
            
            if not filings:
                raise ValueError(f"No {form_type} filings found for {ticker}")
            
            latest_filing = filings[0]
            return self.download_filing(cik, latest_filing['accessionNumber'])
            
        except Exception as e:
            logger.error(f"Error downloading latest filing for {ticker}: {e}")
            raise
    
    def search_filings_by_cik(self, cik: str) -> List[str]:
        """
        Get available filing types for a CIK (useful for exploration)
        
        Args:
            cik: Company CIK number
            
        Returns:
            List of available form types
        """
        try:
            cik_formatted = str(cik).zfill(10)
            url = f"https://data.sec.gov/submissions/CIK{cik_formatted}.json"
            
            time.sleep(self.config.REQUEST_DELAY)
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if 'filings' in data and 'recent' in data['filings']:
                forms = data['filings']['recent'].get('form', [])
                unique_forms = sorted(list(set(forms)))
                logger.info(f"Found {len(unique_forms)} unique form types for CIK {cik}")
                return unique_forms
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching filings for CIK {cik}: {e}")
            return []