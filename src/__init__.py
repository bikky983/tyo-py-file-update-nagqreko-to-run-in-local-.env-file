"""
Nepali News Summarizer - Source Package

This package contains the core functionality for scraping and extracting Nepali news articles.

Modules:
    scraper_links: Web scraping for article links from nepalipaisa.com
    content_extractor: Complete content extraction with browser fallback
    utils: HTTP utilities and helper functions
"""

__version__ = "1.0.0"
__author__ = "Nepali News Summarizer Team"

# Import main functions for easy access
from .scraper_links import get_multi_source_articles
from .content_extractor import extract_article_content
from .utils import get_polite_headers, create_session_with_retries

__all__ = [
    'get_multi_source_articles',
    'extract_article_content',
    'get_polite_headers',
    'create_session_with_retries'
]
