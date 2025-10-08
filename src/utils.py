"""
Utility functions for the Nepali News Summarizer project.
Contains HTTP helpers, headers, and common functions.
"""

import time
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def get_polite_headers() -> Dict[str, str]:
    """
    Returns polite HTTP headers for web scraping.
    
    Returns:
        Dict[str, str]: Headers dictionary with User-Agent and other polite headers
    """
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


def create_session_with_retries(retries: int = 3, backoff_factor: float = 0.3) -> requests.Session:
    """
    Creates a requests session with retry strategy.
    
    Args:
        retries (int): Number of retry attempts
        backoff_factor (float): Backoff factor for retries
        
    Returns:
        requests.Session: Configured session with retry strategy
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=retries,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=backoff_factor
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def safe_request(url: str, timeout: int = 10, delay: float = 1.0) -> requests.Response:
    """
    Makes a safe HTTP request with polite headers, timeout, and rate limiting.
    
    Args:
        url (str): URL to request
        timeout (int): Request timeout in seconds
        delay (float): Delay before request for rate limiting
        
    Returns:
        requests.Response: HTTP response object
        
    Raises:
        requests.RequestException: If request fails after retries
    """
    # Rate limiting - be polite
    time.sleep(delay)
    
    session = create_session_with_retries()
    headers = get_polite_headers()
    
    try:
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        raise requests.RequestException(f"Failed to fetch {url}: {str(e)}")


def extract_domain(url: str) -> str:
    """
    Extracts domain from URL.
    
    Args:
        url (str): Full URL
        
    Returns:
        str: Domain portion of the URL
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
