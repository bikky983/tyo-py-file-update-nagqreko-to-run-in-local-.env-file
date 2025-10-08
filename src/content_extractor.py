#!/usr/bin/env python3
"""
Content Extractor for Nepali News Summarizer
============================================

This module provides comprehensive content extraction for Nepali news articles,
combining standard HTTP parsing with browser-based JavaScript rendering fallback.

Features:
- Intelligent method selection based on domain
- Browser fallback for JavaScript-heavy sites
- Content cleaning and dateline removal
- Unicode preservation for Nepali text
- Comprehensive error handling

Usage:
    from src.content_extractor import extract_article_content
    
    result = extract_article_content("https://example.com/article")
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup, Tag, NavigableString

# Import utilities
from .utils import get_polite_headers, create_session_with_retries

# Optional browser fallback import
try:
    from playwright.sync_api import sync_playwright
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    async_playwright = None

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MAX_BODY_LENGTH = 5000  # characters
DEFAULT_TIMEOUT = 30  # seconds

# Nepali date patterns and mappings
NEPALI_MONTHS = {
    'बैशाख': 1, 'जेठ': 2, 'असार': 3, 'साउन': 4, 'भदौ': 5, 'असोज': 6,
    'कार्तिक': 7, 'मंसिर': 8, 'पुष': 9, 'माघ': 10, 'फागुन': 11, 'चैत': 12,
    'बैसाख': 1, 'भाद्र': 5, 'आश्विन': 6, 'कात्तिक': 7, 'मार्ग': 8, 'पौष': 9
}

NEPALI_WEEKDAYS = ['आइतबार', 'सोमबार', 'मंगलबार', 'बुधबार', 'बिहिबार', 'शुक्रबार', 'शनिबार']

def extract_publish_time(soup: BeautifulSoup, url: str) -> Optional[datetime]:
    """
    Extract publish time from article page.
    
    Args:
        soup: BeautifulSoup object of the article page
        url: Article URL for domain-specific parsing
        
    Returns:
        datetime object if found, None otherwise
    """
    domain = urlparse(url).netloc.lower()
    
    # Common selectors for publish time
    time_selectors = [
        'time[datetime]',
        '.publish-date', '.published-date', '.date-published',
        '.article-date', '.post-date', '.news-date',
        '.meta-date', '.entry-date', '.timestamp',
        '[class*="date"]', '[class*="time"]',
        '.article-meta time', '.post-meta time'
    ]
    
    # Try structured data first
    for selector in time_selectors:
        elements = soup.select(selector)
        for element in elements:
            # Check for datetime attribute
            if element.get('datetime'):
                try:
                    return datetime.fromisoformat(element['datetime'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Check text content
            text = element.get_text().strip()
            if text:
                parsed_time = parse_nepali_datetime(text)
                if parsed_time:
                    return parsed_time
    
    # Domain-specific parsing
    if 'nepalipaisa.com' in domain:
        return extract_nepalipaisa_time(soup)
    elif 'bikashnews.com' in domain:
        return extract_bikashnews_time(soup)
    elif 'merolagani.com' in domain:
        return extract_merolagani_time(soup)
    
    # Fallback: search for date patterns in text
    return extract_time_from_text(soup.get_text())

def parse_nepali_datetime(text: str) -> Optional[datetime]:
    """
    Parse Nepali datetime text into datetime object.
    
    Handles formats like:
    - "२० आश्विन २०८२, सोमबार"
    - "२०८२ असोज १५, १२:३० बजे"
    - "२ घण्टा अगाडि"
    """
    text = text.strip()
    
    # Handle relative times (X घण्टा अगाडि, X मिनेट अगाडि)
    relative_match = re.search(r'(\d+)\s*(घण्टा|मिनेट)\s*अगाडि', text)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        
        if unit == 'घण्टा':
            return datetime.now() - timedelta(hours=amount)
        elif unit == 'मिनेट':
            return datetime.now() - timedelta(minutes=amount)
    
    # Handle Nepali date format: "२० आश्विन २०८२"
    nepali_date_match = re.search(r'(\d+)\s*([^\s,]+)\s*(\d{4})', text)
    if nepali_date_match:
        day = int(nepali_date_match.group(1))
        month_name = nepali_date_match.group(2)
        year = int(nepali_date_match.group(3))
        
        if month_name in NEPALI_MONTHS:
            # Convert Nepali date to approximate Gregorian
            # This is a rough conversion - for exact conversion, you'd need a proper Nepali calendar library
            nepali_month = NEPALI_MONTHS[month_name]
            
            # Rough conversion: Nepali year - 56/57 = Gregorian year
            gregorian_year = year - 56 if nepali_month <= 3 else year - 57
            
            try:
                # Approximate month mapping (this is rough)
                gregorian_month = nepali_month + 3 if nepali_month <= 9 else nepali_month - 9
                if gregorian_month > 12:
                    gregorian_month -= 12
                    gregorian_year += 1
                
                return datetime(gregorian_year, gregorian_month, min(day, 28))
            except:
                pass
    
    return None

def extract_nepalipaisa_time(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract time from Nepali Paisa articles."""
    # Look for specific patterns in Nepali Paisa
    meta_elements = soup.select('.article-meta, .post-meta, .news-meta')
    for element in meta_elements:
        text = element.get_text()
        parsed = parse_nepali_datetime(text)
        if parsed:
            return parsed
    return None

def extract_bikashnews_time(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract time from Bikash News articles."""
    # Look for date in Bikash News format
    date_elements = soup.select('.date, .published, .article-date')
    for element in date_elements:
        text = element.get_text()
        parsed = parse_nepali_datetime(text)
        if parsed:
            return parsed
    return None

def extract_merolagani_time(soup: BeautifulSoup) -> Optional[datetime]:
    """Extract time from Mero Lagani articles."""
    # Mero Lagani might have different format
    time_elements = soup.select('.time, .date, .published')
    for element in time_elements:
        text = element.get_text()
        parsed = parse_nepali_datetime(text)
        if parsed:
            return parsed
    return None

def extract_time_from_text(text: str) -> Optional[datetime]:
    """Extract time from general text content."""
    # Look for common Nepali time patterns in the full text
    lines = text.split('\n')[:10]  # Check first 10 lines
    
    for line in lines:
        parsed = parse_nepali_datetime(line)
        if parsed:
            return parsed
    
    return None

# Create logs directory for screenshots
LOGS_DIR = Path(__file__).parent.parent / 'logs' / 'screenshots'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Content selectors (in order of preference)
ARTICLE_SELECTORS = [
    # Nepali news site specific patterns (prioritize these)
    '.news-detail-content',
    '.article-detail',
    '.news-content',
    '.news-body',
    '.detail-content',
    '.story-content',
    '.post-detail',
    
    # Merolagani specific selectors
    '#ctl00_ContentPlaceHolder1_NewsDetailPanel',
    '.news-detail',
    '#ContentPlaceHolder1_NewsDetailPanel',
    '[id*="NewsDetail"]',
    
    # Semantic HTML5 elements
    'article',
    'main article',
    '[role="main"] article',
    
    # Common content containers
    '.post-content',
    '.entry-content', 
    '.article-content',
    '.content-area',
    '.post-body',
    '.article-body',
    
    # Generic content patterns
    'div[class*="content"]',
    'div[class*="post"]',
    'div[class*="article"]',
    'div[class*="body"]',
    'div[class*="text"]',
    
    # ID-based selectors
    '#content',
    '#main-content',
    '#article-content',
    
    # Fallback to main content areas
    'main',
    '.main',
    '#main'
]

# Selectors for metadata extraction
TITLE_SELECTORS = [
    'h1.entry-title',
    'h1.post-title', 
    'h1.article-title',
    '.title h1',
    'article h1',
    'h1',
    'title'
]

AUTHOR_SELECTORS = [
    '.author',
    '.byline',
    '.post-author',
    '.article-author',
    '.author-name',
    '[rel="author"]',
    '.writer',
    '.journalist'
]

DATE_SELECTORS = [
    'time[datetime]',
    '.published',
    '.post-date',
    '.article-date',
    '.date',
    '.timestamp',
    'meta[property="article:published_time"]',
    'meta[name="publish-date"]'
]

# Known JavaScript-heavy domains
JS_HEAVY_DOMAINS = [
    'nepalipaisa.com',
    'onlinekhabar.com',
    'ekantipur.com',
    'merolagani.com',
    'bikashnews.com'
]

# Navigation content patterns to exclude
NAV_PATTERNS = [
    'Home News Latest News Stock Market',
    'Popular News Interviews Market Analysis',
    'Investment Opportunities IPO FPO',
    'Contact Us Feedback FAQ',
    'Training Calculator',
    'Share Manager Portfolio'
]

# Content cleanup patterns (remove from beginning/end)
CLEANUP_PATTERNS = [
    'Nepali Paisa In this article:',
    'Top Stories',
    'Related News',
    'Share this article',
    'Follow us on',
    'Subscribe to',
    'Advertisement'
]


def clean_text(element) -> str:
    """Extract and clean text from BeautifulSoup element."""
    if isinstance(element, str):
        return element.strip()
    
    if isinstance(element, (Tag, NavigableString)):
        # Get text and normalize Unicode
        text = element.get_text(separator=' ', strip=True)
        
        # Normalize Unicode (important for Nepali text)
        import unicodedata
        text = unicodedata.normalize('NFC', text)
        
        return text
    
    return str(element).strip()


def is_navigation_content(text: str) -> bool:
    """Check if text appears to be navigation content."""
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in NAV_PATTERNS)


def has_substantial_nepali_content(text: str) -> bool:
    """Check if text has substantial Nepali content."""
    if len(text) < 20:
        return False
    # Count Devanagari characters
    nepali_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
    return nepali_chars > 5


def extract_merolagani_content(element) -> str:
    """Extract clean content specifically from Merolagani articles."""
    if not element:
        return ""
    
    # Look for the actual article content paragraphs
    content_parts = []
    
    # Find all text nodes that look like article content
    for child in element.descendants:
        if child.name in ['p', 'div'] and child.string:
            text = child.string.strip()
            
            # Skip if it's navigation, title, or other non-content
            if (len(text) > 30 and 
                not any(skip in text.lower() for skip in [
                    'facebook', 'twitter', 'whatsapp', 'copy link', 'popular news',
                    'more', 'log in', 'edit account', 'change password', 'search',
                    'कम्पनीले गरे लाभांश', 'प्रतिशतसम्म लाभांश', 'sep ', 'am', 'pm'
                ]) and
                # Must contain Nepali characters
                any('\u0900' <= char <= '\u097F' for char in text)):
                content_parts.append(text)
    
    # Also try to get direct text content between navigation elements
    if not content_parts:
        # Get all text and filter out navigation
        all_text = element.get_text(separator='\n', strip=True)
        lines = all_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if (len(line) > 30 and 
                not any(skip in line.lower() for skip in [
                    'facebook', 'twitter', 'whatsapp', 'copy link', 'popular news',
                    'more', 'log in', 'edit account', 'change password', 'search',
                    'कम्पनीले गरे लाभांश', 'प्रतिशतसम्म लाभांश', 'sep ', 'am', 'pm',
                    'edit account', 'verify mobile', 'remove account', 'log out'
                ]) and
                any('\u0900' <= char <= '\u097F' for char in line)):
                content_parts.append(line)
    
    return ' '.join(content_parts) if content_parts else ""


def clean_article_content(text: str) -> str:
    """Clean article content by removing navigation elements and datelines."""
    if not text:
        return text
    
    cleaned_text = text.strip()
    
    # Remove cleanup patterns from beginning and end
    for pattern in CLEANUP_PATTERNS:
        # Remove from beginning (case insensitive)
        if cleaned_text.lower().startswith(pattern.lower()):
            cleaned_text = cleaned_text[len(pattern):].strip()
        
        # Remove from end (case insensitive)
        if cleaned_text.lower().endswith(pattern.lower()):
            cleaned_text = cleaned_text[:-len(pattern)].strip()
    
    # Remove dateline patterns (location : at beginning)
    # Common Nepali datelines: काठमाडौं :, पोखरा :, चितवन :, etc.
    dateline_pattern = r'^[^\s]+\s*:\s*'
    if re.match(dateline_pattern, cleaned_text):
        cleaned_text = re.sub(dateline_pattern, '', cleaned_text).strip()
    
    # Remove multiple spaces and normalize whitespace
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    return cleaned_text.strip()


def download_article(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Download article HTML using HTTP requests."""
    logger.info(f"Downloading article: {url}")
    
    session = create_session_with_retries()
    
    try:
        response = session.get(
            url,
            headers=get_polite_headers(),
            timeout=timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        
        logger.info(f"Downloaded {len(response.content)} bytes")
        return response.text
        
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        raise


def extract_title(soup: BeautifulSoup, url: str) -> str:
    """Extract article title from HTML."""
    for selector in TITLE_SELECTORS:
        try:
            element = soup.select_one(selector)
            if element:
                title = clean_text(element)
                if title and len(title) > 5:
                    logger.debug(f"Found title using selector '{selector}': {title[:50]}...")
                    return title
        except Exception as e:
            logger.debug(f"Error with title selector '{selector}': {e}")
            continue
    
    # Fallback: extract from URL
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        if path_parts:
            title = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
            logger.debug(f"Using URL-based title: {title}")
            return title
    except Exception:
        pass
    
    return "Unknown Title"


def extract_author(soup: BeautifulSoup) -> Optional[str]:
    """Extract article author from HTML."""
    for selector in AUTHOR_SELECTORS:
        try:
            element = soup.select_one(selector)
            if element:
                author = clean_text(element)
                if author and len(author) < 100:  # Reasonable author name length
                    logger.debug(f"Found author using selector '{selector}': {author}")
                    return author
        except Exception as e:
            logger.debug(f"Error with author selector '{selector}': {e}")
            continue
    
    return None


def extract_published_date(soup: BeautifulSoup) -> Optional[str]:
    """Extract article published date from HTML."""
    for selector in DATE_SELECTORS:
        try:
            element = soup.select_one(selector)
            if element:
                # Try datetime attribute first
                date_value = element.get('datetime') or element.get('content')
                if date_value:
                    logger.debug(f"Found date using selector '{selector}': {date_value}")
                    return date_value
                
                # Fall back to text content
                date_text = clean_text(element)
                if date_text and len(date_text) < 50:  # Reasonable date length
                    logger.debug(f"Found date using selector '{selector}': {date_text}")
                    return date_text
        except Exception as e:
            logger.debug(f"Error with date selector '{selector}': {e}")
            continue
    
    return None


def extract_body_text(soup: BeautifulSoup, url: str, max_length: int = DEFAULT_MAX_BODY_LENGTH) -> str:
    """Extract main article body text using source-specific strategies."""
    
    # Use Merolagani-specific extraction only for Merolagani
    if 'merolagani.com' in url:
        return extract_merolagani_content_full(soup, max_length)
    elif 'bikashnews.com' in url:
        return extract_bikashnews_content_full(soup, max_length)
    else:
        # Use the original working method for Nepali Paisa and other sites
        return extract_generic_content(soup, max_length)


def extract_nepalipaisa_content(soup: BeautifulSoup, max_length: int) -> str:
    """Extract content specifically from Nepali Paisa articles."""
    content_parts = []
    
    # Nepali Paisa specific selectors
    selectors = [
        '.news-detail-content',
        '.article-content',
        '.post-content',
        '.content-area',
        'article .content',
        '.entry-content',
        'div[class*="content"] p',
        '.main-content p',
        'article p'
    ]
    
    for selector in selectors:
        try:
            elements = soup.select(selector)
            for element in elements:
                text = clean_text(element)
                if text and len(text) > 50 and has_substantial_nepali_content(text):
                    if not is_navigation_content(text):
                        content_parts.append(text)
        except Exception as e:
            logger.debug(f"Error with Nepali Paisa selector '{selector}': {e}")
            continue
    
    # If no specific content found, try paragraph extraction
    if not content_parts:
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = clean_text(p)
            if text and len(text) > 30 and has_substantial_nepali_content(text):
                if not is_navigation_content(text):
                    content_parts.append(text)
    
    result = ' '.join(content_parts)
    return result[:max_length] if len(result) > max_length else result


def extract_bikashnews_content(soup: BeautifulSoup, max_length: int) -> str:
    """Extract content specifically from Bikash News articles."""
    content_parts = []
    
    # Bikash News specific selectors
    selectors = [
        '.story-content',
        '.news-content',
        '.article-body',
        '.post-content',
        'article .content',
        '.main-content',
        'div[class*="content"] p',
        'article p'
    ]
    
    for selector in selectors:
        try:
            elements = soup.select(selector)
            for element in elements:
                text = clean_text(element)
                if text and len(text) > 50 and has_substantial_nepali_content(text):
                    if not is_navigation_content(text):
                        content_parts.append(text)
        except Exception as e:
            logger.debug(f"Error with Bikash News selector '{selector}': {e}")
            continue
    
    # If no specific content found, try paragraph extraction
    if not content_parts:
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = clean_text(p)
            if text and len(text) > 30 and has_substantial_nepali_content(text):
                if not is_navigation_content(text):
                    content_parts.append(text)
    
    result = ' '.join(content_parts)
    return result[:max_length] if len(result) > max_length else result


def extract_bikashnews_content_full(soup: BeautifulSoup, max_length: int) -> str:
    """Extract content specifically from Bikash News articles with enhanced cleaning."""
    
    # First, try to find the main article content and exclude sidebar
    main_content = extract_bikashnews_main_article(soup)
    if main_content and len(main_content) > 100:
        return clean_bikashnews_content(main_content)[:max_length]
    
    # Fallback: Try the existing Bikash News extraction function
    content_div = soup.select_one('div[class*="content"]') or soup.select_one('.content')
    if content_div:
        extracted = extract_bikashnews_content(content_div, max_length * 2)  # Get more content for cleaning
        if extracted and len(extracted) > 100:
            return clean_bikashnews_content(extracted)[:max_length]
    
    # Final fallback to paragraph extraction (excluding sidebar)
    content_parts = []
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        # Skip if paragraph is in sidebar or related news section
        if is_bikashnews_sidebar_content(p):
            continue
            
        text = clean_text(p)
        if text and len(text) > 30 and has_substantial_nepali_content(text):
            if not is_navigation_content(text) and not is_bikashnews_unwanted_content(text):
                content_parts.append(text)
    
    result = ' '.join(content_parts)
    return clean_bikashnews_content(result)[:max_length]


def extract_bikashnews_main_article(soup: BeautifulSoup) -> str:
    """Extract main article content from Bikash News, excluding sidebar."""
    content_parts = []
    
    # Try to find the main article container
    main_selectors = [
        'div[class*="story-content"]',
        'div[class*="article-content"]',
        'div[class*="news-content"]',
        'div[class*="main-content"]',
        '.post-content',
        'article',
        'div[id*="story"]',
        'div[id*="article"]'
    ]
    
    for selector in main_selectors:
        main_containers = soup.select(selector)
        for container in main_containers:
            # Skip if this looks like a sidebar or related news section
            if is_bikashnews_sidebar_content(container):
                continue
                
            # Extract text from this container
            text = container.get_text(separator=' ', strip=True)
            if text and len(text) > 200:  # Must be substantial
                # Clean and filter the text
                lines = text.split('।')  # Split by Nepali sentence ending
                for line in lines:
                    line = line.strip()
                    if (len(line) > 30 and 
                        not is_bikashnews_unwanted_content(line) and
                        not is_bikashnews_sidebar_content_text(line) and
                        any('\u0900' <= char <= '\u097F' for char in line)):
                        content_parts.append(line)
                
                if content_parts:
                    return '।'.join(content_parts)
    
    return ""


def is_bikashnews_sidebar_content(element) -> bool:
    """Check if an element is part of the sidebar or related news."""
    if not element:
        return False
    
    # Check element classes and IDs for sidebar indicators
    element_str = str(element)
    sidebar_indicators = [
        'sidebar', 'related', 'popular', 'trending', 'more-news',
        'right-column', 'side-content', 'widget', 'advertisement',
        'share-news', 'social-share', 'pdf-viewer'
    ]
    
    for indicator in sidebar_indicators:
        if indicator in element_str.lower():
            return True
    
    return False


def is_bikashnews_sidebar_content_text(text: str) -> bool:
    """Check if text content is from sidebar/related news."""
    sidebar_patterns = [
        'Share News लोकप्रिय',
        'लाभांश सिजन',
        'नेपाल एसबिआई',
        'भूषण राणा',
        'एनआईसी एशिया बैंक',
        'सम्बन्धित खबर',
        'Loading WEBGL',
        'Loading PDF',
        'Share Previous Page',
        'Toggle Outline',
        'Zoom In',
        'Download PDF'
    ]
    
    return any(pattern in text for pattern in sidebar_patterns)


def is_bikashnews_unwanted_content(text: str) -> bool:
    """Check if text is unwanted content like PDF controls, duplicate titles, etc."""
    unwanted_patterns = [
        # PDF viewer controls
        'Loading WEBGL 3D',
        'Loading PDF 100%',
        'Share Previous Page',
        'Toggle Outline/Bookmark',
        'Toggle Thumbnails',
        'Zoom In Zoom Out',
        'Toggle Fullscreen',
        'Download PDF File',
        'Double Page Mode',
        'Goto First Page',
        'Goto Last Page',
        'Turn on/off Sound',
        
        # Sidebar content
        'Share News लोकप्रिय',
        'सबै पढ्नुहोस्',
        'लाभांश सिजन',
        'नेपाल एसबिआई',
        'भूषण राणा',
        'एनआईसी एशिया बैंक',
        'सम्बन्धित खबर',
        
        # Duplicate metadata (if it repeats the title)
        'विकासन्युज आइतबार',
        'अ अ काठमाडौं'
    ]
    
    return any(pattern in text for pattern in unwanted_patterns)


def clean_bikashnews_content(text: str) -> str:
    """Clean Bikash News content by removing unwanted sections."""
    if not text:
        return text
    
    # Remove unwanted patterns from the beginning and end
    unwanted_start_patterns = [
        # Remove duplicate title and metadata at start
        r'^[^।]*विकासन्युज आइतबार[^।]*अ अ काठमाडौं\s*।\s*',
        # Remove any PDF loading text
        r'^[^।]*Loading[^।]*।\s*',
    ]
    
    for pattern in unwanted_start_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    
    # Split into sentences and filter out unwanted content
    sentences = text.split('।')  # Split by Nepali sentence ending
    clean_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and not is_bikashnews_unwanted_content(sentence):
            # Additional cleaning for partial matches
            if not any(unwanted in sentence for unwanted in [
                'Loading', 'Share', 'Toggle', 'Zoom', 'Download', 'PDF',
                'लाभांश सिजन', 'नेपाल एसबिआई', 'भूषण राणा',
                'सम्बन्धित खबर', 'विकासन्युज आइतबार'
            ]):
                clean_sentences.append(sentence)
    
    # Join sentences back
    cleaned_text = '।'.join(clean_sentences).strip()
    
    # Remove any remaining unwanted content at the end
    end_patterns = [
        r'Share News लोकप्रिय.*$',
        r'सम्बन्धित खबर.*$',
        r'Loading.*$'
    ]
    
    for pattern in end_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
    
    return cleaned_text.strip()


def extract_merolagani_content_full(soup: BeautifulSoup, max_length: int) -> str:
    """Extract content specifically from Merolagani articles."""
    
    # First, try to find the main article content area and exclude sidebar
    main_content = extract_merolagani_main_article(soup)
    if main_content and len(main_content) > 100:
        return clean_merolagani_content(main_content)[:max_length]
    
    # Fallback: Try the existing Merolagani extraction function
    content_div = soup.select_one('div[class*="content"]') or soup.select_one('.content')
    if content_div:
        extracted = extract_merolagani_content(content_div)
        if extracted and len(extracted) > 100:
            return clean_merolagani_content(extracted)[:max_length]
    
    # Final fallback to paragraph extraction (excluding sidebar)
    content_parts = []
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        # Skip if paragraph is in sidebar or related news section
        if is_merolagani_sidebar_content(p):
            continue
            
        text = clean_text(p)
        if text and len(text) > 30 and has_substantial_nepali_content(text):
            if not is_navigation_content(text) and not is_merolagani_article_end(text):
                content_parts.append(text)
    
    result = ' '.join(content_parts)
    return clean_merolagani_content(result)[:max_length]


def extract_merolagani_main_article(soup: BeautifulSoup) -> str:
    """Extract main article content from Merolagani, excluding sidebar."""
    content_parts = []
    
    # Try to find the main article container (usually left side)
    main_selectors = [
        'div[class*="news-detail"]',
        'div[class*="article-content"]',
        'div[class*="main-content"]',
        '.news-content',
        'article',
        'div[id*="news"]',
        'div[id*="article"]'
    ]
    
    for selector in main_selectors:
        main_containers = soup.select(selector)
        for container in main_containers:
            # Skip if this looks like a sidebar or related news section
            if is_merolagani_sidebar_content(container):
                continue
                
            # Extract text from this container
            text = container.get_text(separator=' ', strip=True)
            if text and len(text) > 200:  # Must be substantial
                # Clean and filter the text
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if (len(line) > 30 and 
                        not is_merolagani_article_end(line) and
                        not is_merolagani_sidebar_content_text(line) and
                        any('\u0900' <= char <= '\u097F' for char in line)):
                        content_parts.append(line)
                
                if content_parts:
                    return ' '.join(content_parts)
    
    return ""


def is_merolagani_sidebar_content(element) -> bool:
    """Check if an element is part of the sidebar or related news."""
    if not element:
        return False
    
    # Check element classes and IDs for sidebar indicators
    element_str = str(element)
    sidebar_indicators = [
        'sidebar', 'related', 'popular', 'trending', 'more-news',
        'right-column', 'side-content', 'widget', 'advertisement'
    ]
    
    for indicator in sidebar_indicators:
        if indicator in element_str.lower():
            return True
    
    # Check if element contains multiple short news headlines (typical of sidebar)
    text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
    if text:
        # Count question marks (headlines often end with ?)
        question_marks = text.count('?')
        # If multiple questions in short text, likely sidebar
        if question_marks > 2 and len(text) < 500:
            return True
    
    return False


def is_merolagani_sidebar_content_text(text: str) -> bool:
    """Check if text content is from sidebar/related news."""
    sidebar_patterns = [
        'शेयर बजार', 'आईपीओ', 'कम्पनी', 'लाभांश', 'नेप्से',
        'ट्रयाक रकेर्ड', 'कालो सोमबार', 'राइट शेयर',
        'पाइपलाईन', 'दशैं पछि', 'मनसुन बहिर्गमन',
        'अष्टमी,नवमी', 'टीकाकै दिन', 'पूर्वानुमान रिपाेर्ट'
    ]
    
    return any(pattern in text for pattern in sidebar_patterns)


def is_merolagani_article_end(line: str) -> bool:
    """Check if a line indicates the end of the main article content."""
    # Patterns that indicate article has ended
    end_patterns = [
        'दशैकाे भाेलीपल्टदेखि',  # Other article headlines
        'दशैं पछि के होला',
        'वर्षको \'ट्रयाक रकेर्ड\'',
        'शेयर बजारमा \'कालो सोमबार\'',
        'प्राथमिक हुदै दोस्रो बजार',
        'आईपीओ र राइट शेयर',
        'दशैँको टीकाकै दिन',
        'मनसुन बहिर्गमन',
        'अष्टमी,नवमी र दशमी',
        'मौसम पूर्वानुमान रिपाेर्ट',
        'सुचना तथा प्रसारण विभाग',  # Footer
        'प्रकाशक -',
        'एस्ट्रिक टेक्नोलोजी',
        'editor@merolagani.com',
        'द.न. ४४०',
        'रिपाेर्ट सुचना तथा प्रसारण',
        '? दशैं पछि के होला',  # Question marks followed by other headlines
        '? ५ वर्षको',
        'ले दिएको चेतावनी प्राथमिक',
        'पाइपलाईनमा ? दशैँको'
    ]
    
    return any(pattern in line for pattern in end_patterns)


def clean_merolagani_content(text: str) -> str:
    """Clean Merolagani content by removing unwanted sections."""
    if not text:
        return text
    
    # Split into sentences and filter out unwanted content
    sentences = text.split('।')  # Split by Nepali sentence ending
    clean_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and not is_merolagani_article_end(sentence):
            # Additional cleaning for partial matches
            if not any(unwanted in sentence for unwanted in [
                'शेयर बजार', 'आईपीओ', 'राइट शेयर', 'मनसुन बहिर्गमन',
                'प्रकाशक', 'editor@', 'द.न.', 'एस्ट्रिक टेक्नोलोजी',
                'सुचना तथा प्रसारण', 'ट्रयाक रकेर्ड', 'कालो सोमबार'
            ]):
                clean_sentences.append(sentence)
    
    return '।'.join(clean_sentences).strip()


def extract_generic_content(soup: BeautifulSoup, max_length: int) -> str:
    """Generic content extraction for unknown sites."""
    body_candidates = []
    
    # Try each selector in order of preference
    for selector in ARTICLE_SELECTORS:
        try:
            elements = soup.select(selector)
            for element in elements:
                if element:
                    text = clean_text(element)
                    if text and len(text) > 100:  # Must have substantial content
                        # Skip if it's navigation content
                        if is_navigation_content(text):
                            logger.debug(f"Skipping navigation content from '{selector}'")
                            continue
                        
                        body_candidates.append((text, len(text), selector))
                        logger.debug(f"Found content using '{selector}': {len(text)} chars")
        except Exception as e:
            logger.debug(f"Error with selector '{selector}': {e}")
            continue
    
    # If no good candidates found, try paragraph-based extraction
    if not body_candidates:
        logger.debug("No content found with article selectors, trying paragraph extraction")
        paragraphs = soup.find_all('p')
        if paragraphs:
            # Filter paragraphs to exclude navigation
            good_paragraphs = []
            for p in paragraphs:
                p_text = clean_text(p)
                if p_text and len(p_text) > 20 and not is_navigation_content(p_text):
                    good_paragraphs.append(p_text)
            
            if good_paragraphs:
                combined_text = ' '.join(good_paragraphs)
                if len(combined_text) > 50:
                    body_candidates.append((combined_text, len(combined_text), 'filtered_paragraphs'))
    
    # If still no candidates, try a more aggressive approach
    if not body_candidates:
        logger.debug("Trying aggressive content extraction")
        # Look for any element with substantial text that contains Nepali characters
        all_elements = soup.find_all(['div', 'span', 'section', 'article', 'p'])
        for element in all_elements:
            text = clean_text(element)
            if (len(text) > 100 and 
                has_substantial_nepali_content(text) and 
                not is_navigation_content(text)):
                body_candidates.append((text, len(text), 'nepali_content_element'))
                logger.debug(f"Found Nepali content element: {len(text)} chars")
    
    # Last resort: look for any text with Nepali characters, even if short
    if not body_candidates:
        logger.debug("Last resort: looking for any Nepali text")
        all_text_elements = soup.find_all(string=True)
        nepali_texts = []
        
        for text_node in all_text_elements:
            text = str(text_node).strip()
            if (len(text) > 30 and 
                has_substantial_nepali_content(text) and
                not is_navigation_content(text)):
                # Check if parent is not script/style
                parent = text_node.parent
                if parent and parent.name not in ['script', 'style', 'title']:
                    nepali_texts.append(text)
        
        if nepali_texts:
            combined_nepali = ' '.join(nepali_texts)
            if len(combined_nepali) > 50:
                body_candidates.append((combined_nepali, len(combined_nepali), 'combined_nepali_text'))
                logger.debug(f"Found combined Nepali text: {len(combined_nepali)} chars")
    
    # Select the best candidate
    if body_candidates:
        # Prefer candidates with Nepali content, then by length
        nepali_candidates = [(text, length, selector) for text, length, selector in body_candidates 
                           if has_substantial_nepali_content(text)]
        
        if nepali_candidates:
            # Sort Nepali candidates by length
            nepali_candidates.sort(key=lambda x: x[1], reverse=True)
            best_text, best_length, best_selector = nepali_candidates[0]
        else:
            # Fall back to longest candidate
            body_candidates.sort(key=lambda x: x[1], reverse=True)
            best_text, best_length, best_selector = body_candidates[0]
        
        logger.info(f"Selected body text from '{best_selector}': {best_length} characters")
        
        # Clean the content to remove navigation elements
        best_text = clean_article_content(best_text)
        logger.debug(f"Cleaned content: {len(best_text)} characters")
        
        # Truncate if necessary
        if len(best_text) > max_length:
            best_text = best_text[:max_length] + "..."
            logger.debug(f"Truncated body text to {max_length} characters")
        
        return best_text
    
    logger.warning("No substantial body text found")
    
    # Final fallback: extract Nepali text from title if available
    title_elem = soup.find('title')
    if title_elem:
        title_text = clean_text(title_elem)
        if has_substantial_nepali_content(title_text):
            logger.info("Using title as body text fallback")
            return title_text
    
    return ""


def parse_html_content(html: str, url: str, max_body_length: int = DEFAULT_MAX_BODY_LENGTH) -> Dict:
    """Parse HTML content and extract metadata and body text."""
    logger.info(f"Parsing HTML content from: {url}")
    
    try:
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract metadata and content
        title = extract_title(soup, url)
        author = extract_author(soup)
        
        # Try to extract publish time using our new function
        publish_time = extract_publish_time(soup, url)
        published = publish_time.isoformat() if publish_time else extract_published_date(soup)
        
        # Extract body text
        body_text = extract_body_text(soup, url, max_body_length)
        
        # Determine parser status - require substantial content and Nepali text
        has_nepali = any('\u0900' <= char <= '\u097F' for char in body_text) if body_text else False
        is_substantial = len(body_text.strip()) > 200 if body_text else False
        
        parser_status = 'success' if body_text and is_substantial and has_nepali else 'failed'
        
        result = {
            'url': url,
            'title': title,
            'published': published,
            'author': author,
            'body_text': body_text,
            'parser_status': parser_status
        }
        
        logger.info(f"Parsing completed with status: {parser_status}")
        logger.debug(f"Extracted - Title: {title[:50]}..., Body: {len(body_text)} chars")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to parse HTML from {url}: {e}")
        return {
            'url': url,
            'title': 'Parse Error',
            'published': None,
            'author': None,
            'body_text': '',
            'parser_status': 'failed'
        }


async def fetch_rendered_html_async(
    url: str, 
    timeout: int = 30000,
    save_screenshot: bool = True
) -> str:
    """Fetch HTML content after JavaScript rendering using Playwright (async version)."""
    logger.info(f"Fetching rendered HTML for: {url}")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        try:
            # Create page
            page = await browser.new_page()
            
            # Set user agent to avoid bot detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Navigate to page
            logger.debug(f"Navigating to: {url}")
            
            # Use different timeout and wait strategy for different sites
            site_timeout = timeout
            wait_until = 'networkidle'
            
            if 'merolagani.com' in url:
                site_timeout = 30000  # 30 seconds for merolagani
                wait_until = 'load'  # Use 'load' instead of 'networkidle' for faster loading
            
            await page.goto(url, timeout=site_timeout, wait_until=wait_until)
            
            # Try to wait for article content
            article_selectors = ['article', '.post-content', '.article-content', '.news-content', '.content', 'main']
            
            # Add Merolagani-specific selectors
            if 'merolagani.com' in url:
                article_selectors = ['#ctl00_ContentPlaceHolder1_NewsDetailPanel', '[id*="NewsDetail"]'] + article_selectors
            for selector in article_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    logger.debug(f"Found article selector: {selector}")
                    break
                except:
                    continue
            
            # Additional wait for dynamic content
            await page.wait_for_timeout(2000)  # 2 second buffer
            
            # Save screenshot for debugging
            if save_screenshot:
                timestamp = int(time.time())
                screenshot_path = LOGS_DIR / f"page_{timestamp}.png"
                await page.screenshot(path=str(screenshot_path))
                logger.debug(f"Screenshot saved: {screenshot_path}")
            
            # Get rendered HTML
            html = await page.content()
            logger.info(f"Successfully rendered HTML: {len(html)} characters")
            
            return html
            
        finally:
            await browser.close()


def fetch_rendered_html(url: str, timeout: int = 30, save_screenshot: bool = True) -> str:
    """Fetch HTML content after JavaScript rendering using Playwright (sync wrapper)."""
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError(
            "Playwright is not installed. Install with:\n"
            "pip install playwright\n"
            "playwright install"
        )
    
    # Convert timeout to milliseconds
    timeout_ms = timeout * 1000
    
    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        fetch_rendered_html_async(url, timeout_ms, save_screenshot)
    )


def extract_article_content(url: str, max_body_length: int = DEFAULT_MAX_BODY_LENGTH) -> Dict:
    """
    Extract article content with intelligent method selection.
    
    For known JavaScript-heavy sites, this function goes directly to browser-based
    rendering. For other sites, it tries standard HTTP parsing first with browser
    fallback if needed.
    
    Args:
        url: Article URL to parse
        max_body_length: Maximum body text length
        
    Returns:
        Dictionary with keys: url, title, published, author, body_text, parser_status, parser_method
    """
    logger.info(f"Extracting article content: {url}")
    
    # Check if this is a known JS-heavy site
    use_browser_directly = any(domain in url for domain in JS_HEAVY_DOMAINS)
    
    if use_browser_directly:
        logger.info("Detected JavaScript-heavy site, using browser rendering directly")
        return extract_with_browser_rendering(url, max_body_length)
    
    # Try standard HTTP-based parsing for other sites
    try:
        html = download_article(url)
        result = parse_html_content(html, url, max_body_length)
        
        # If parsing was successful, return result
        if result['parser_status'] == 'success':
            logger.info("Standard parsing successful")
            result['parser_method'] = 'standard'
            return result
        
        logger.info("Standard parsing failed, trying browser fallback...")
        
    except Exception as e:
        logger.warning(f"Standard parsing error: {e}, trying browser fallback...")
    
    # Use browser fallback
    return extract_with_browser_rendering(url, max_body_length)


def extract_with_browser_rendering(url: str, max_body_length: int = DEFAULT_MAX_BODY_LENGTH) -> Dict:
    """Extract article content using browser rendering directly."""
    if PLAYWRIGHT_AVAILABLE:
        try:
            logger.info("Using browser rendering to extract JavaScript content")
            rendered_html = fetch_rendered_html(url, timeout=30)
            
            # Parse the rendered HTML
            result = parse_html_content(rendered_html, url, max_body_length)
            
            # Mark as browser rendering in the result
            result['parser_method'] = 'browser_fallback'
            
            if result['parser_status'] == 'success':
                logger.info("Browser rendering extraction successful")
                return result
            else:
                logger.warning("Browser rendering also failed to extract content")
                result['parser_status'] = 'fallback_failed'
                return result
                
        except Exception as e:
            logger.error(f"Browser rendering failed: {e}")
            return {
                'url': url,
                'title': 'Browser Rendering Error',
                'published': None,
                'author': None,
                'body_text': '',
                'parser_status': 'fallback_error',
                'parser_method': 'browser_fallback',
                'fallback_error': str(e)
            }
    else:
        logger.warning("Browser rendering not available (Playwright not installed)")
        return {
            'url': url,
            'title': 'Browser Rendering Unavailable',
            'published': None,
            'author': None,
            'body_text': '',
            'parser_status': 'fallback_unavailable',
            'parser_method': 'browser_fallback'
        }


# CLI test helper
def main():
    """CLI test helper for content extraction."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python -m src.content_extractor <url>")
        print("Example: python -m src.content_extractor https://www.nepalipaisa.com/news-detail/87090")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Configure logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"Testing content extraction with URL: {url}")
    print("=" * 60)
    
    try:
        result = extract_article_content(url)
        
        print(f"Status: {result['parser_status']}")
        print(f"Method: {result.get('parser_method', 'unknown')}")
        print(f"Title: {result['title']}")
        print(f"Author: {result['author']}")
        print(f"Published: {result['published']}")
        print(f"Content length: {len(result['body_text'])} characters")
        
        if result['body_text']:
            preview = result['body_text'][:200] + "..." if len(result['body_text']) > 200 else result['body_text']
            print(f"\nContent preview:")
            print("-" * 40)
            try:
                print(preview)
            except UnicodeEncodeError:
                print("[Content contains Unicode characters that cannot be displayed]")
        
        print("\nContent extraction test completed!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
