"""
Multi-Source Web Scraper for Nepali News Sites
==============================================

This module provides functionality to scrape latest article links from multiple
Nepali news websites including nepalipaisa.com, bikashnews.com, and merolagani.com.

Features:
- Support for multiple news sources
- Source-specific parsing strategies
- Unified output format
- Comprehensive error handling
- Rate limiting and polite scraping
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin, urlparse
import time

import requests
from bs4 import BeautifulSoup
from loguru import logger

from .utils import safe_request, extract_domain


# Supported news sources configuration
NEWS_SOURCES = {
    'nepalipaisa': {
        'name': 'Nepali Paisa',
        'domain': 'https://www.nepalipaisa.com',
        'homepage_selectors': [
            'a[href*="/news-detail/"]',
            'a[href*="news-detail"]',
            '.news-item a',
            '.article-link',
            'a[href*="/news/"]',
            '[class*="news"] a',
            '[class*="article"] a'
        ],
        'article_url_pattern': r'news-detail/\d+',
        'sitemap_url': '/sitemap.xml',
        'rate_limit': 2.0  # seconds between requests
    },
    'bikashnews': {
        'name': 'Bikash News',
        'domain': 'https://www.bikashnews.com',
        'homepage_selectors': [
            'a[href*="/story/"]',
            '.news-item a',
            '.article-link a',
            'a[href*="/news/"]'
        ],
        'article_url_pattern': r'story/\d+',
        'sitemap_url': '/sitemap.xml',
        'rate_limit': 2.0
    },
    'merolagani': {
        'name': 'Mero Lagani',
        'domain': 'https://merolagani.com',
        'news_page': '/NewsList.aspx',
        'homepage_selectors': [
            'a[href*="NewsDetail.aspx"]',
            '.news-item a',
            '.article-link a',
            'a[href*="/news/"]'
        ],
        'article_url_pattern': r'NewsDetail\.aspx',
        'rate_limit': 2.0
    }
}


def get_multi_source_articles(
    sources: Union[str, List[str]] = 'all',
    max_links_per_source: Optional[int] = 6,
    total_max_links: Optional[int] = None,
    hours_back: Optional[int] = 5
) -> List[Dict]:
    """
    Fetch latest article links from multiple Nepali news sources.
    
    Args:
        sources: Source names to scrape ('all', single source name, or list of sources)
        max_links_per_source: Maximum articles per source
        total_max_links: Maximum total articles across all sources
        hours_back: Only include articles from last N hours (None = no time filter)
        
    Returns:
        List of article dictionaries with unified format:
        [{'url': str, 'title': str, 'published': Optional[str], 'source': str}]
    """
    logger.info(f"Starting multi-source scraping: {sources}")
    
    # Calculate cutoff time if hours_back is specified
    # NOTE: Most Nepali news sites don't provide machine-readable timestamps
    # So we rely on scraping latest articles (which are naturally recent)
    # and limiting to max_links_per_source (6) to get only fresh content
    cutoff_time = None
    if hours_back:
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        logger.info(f"Time filter: Targeting articles from last {hours_back} hours (after {cutoff_time.strftime('%Y-%m-%d %H:%M')})")
        logger.info(f"Note: Relying on latest {max_links_per_source} articles per source (sites show newest first)")
    
    # Determine which sources to scrape
    if sources == 'all':
        source_list = list(NEWS_SOURCES.keys())
    elif isinstance(sources, str):
        source_list = [sources] if sources in NEWS_SOURCES else []
    else:
        source_list = [s for s in sources if s in NEWS_SOURCES]
    
    if not source_list:
        logger.error(f"No valid sources found: {sources}")
        return []
    
    logger.info(f"Scraping from sources: {source_list}")
    
    all_articles = []
    
    for source_name in source_list:
        try:
            logger.info(f"Scraping {source_name}...")
            
            # Rate limiting between sources
            if all_articles:  # Not the first source
                time.sleep(NEWS_SOURCES[source_name]['rate_limit'])
            
            source_articles = scrape_source(source_name, max_links_per_source)
            
            # Add source information to each article
            for article in source_articles:
                article['source'] = source_name
                article['source_name'] = NEWS_SOURCES[source_name]['name']
            
            # Filter by time if cutoff_time is specified
            if cutoff_time and source_articles:
                filtered_articles = []
                for article in source_articles:
                    # For now, since we don't have publish times in scraped links,
                    # we assume latest articles are within the time window
                    # This will be improved when we extract actual publish times
                    filtered_articles.append(article)
                
                logger.info(f"Time filtering: Kept {len(filtered_articles)}/{len(source_articles)} articles from {source_name}")
                source_articles = filtered_articles
            
            all_articles.extend(source_articles)
            logger.info(f"Found {len(source_articles)} articles from {source_name}")
            
        except Exception as e:
            logger.error(f"Failed to scrape {source_name}: {e}")
            continue
    
    # Sort by publication date (newest first) and apply total limit
    all_articles = sort_articles_by_freshness(all_articles)
    
    if total_max_links and len(all_articles) > total_max_links:
        all_articles = all_articles[:total_max_links]
        logger.info(f"Limited to {total_max_links} total articles")
    
    logger.info(f"Multi-source scraping completed: {len(all_articles)} total articles")
    return all_articles


def scrape_source(source_name: str, max_links: int) -> List[Dict]:
    """
    Scrape articles from a specific news source.
    
    Args:
        source_name: Name of the source (key in NEWS_SOURCES)
        max_links: Maximum number of articles to return
        
    Returns:
        List of article dictionaries
    """
    if source_name not in NEWS_SOURCES:
        raise ValueError(f"Unknown source: {source_name}")
    
    config = NEWS_SOURCES[source_name]
    
    # Try different scraping strategies based on source
    if source_name == 'merolagani':
        return scrape_merolagani(config, max_links)
    else:
        return scrape_generic_news_site(config, max_links)


def scrape_merolagani(config: Dict, max_links: int) -> List[Dict]:
    """
    Scrape articles from Merolagani (stock market news).
    
    Args:
        config: Source configuration
        max_links: Maximum articles to return
        
    Returns:
        List of article dictionaries
    """
    articles = []
    
    # Try news page first
    news_url = config['domain'] + config.get('news_page', '/NewsList.aspx')
    
    try:
        response = safe_request(news_url)
        if not response:
            return articles
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for news links with various selectors
        selectors = [
            'a[href*="NewsDetail.aspx"]',
            'a[href*="newsdetail"]',
            '.news-title a',
            '.news-item a',
            'td a[href*="NewsDetail"]'
        ]
        
        found_links = set()
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                
                for element in elements:
                    href = element.get('href')
                    if not href:
                        continue
                    
                    # Make absolute URL
                    if href.startswith('/'):
                        url = config['domain'] + href
                    elif href.startswith('http'):
                        url = href
                    else:
                        url = urljoin(config['domain'], href)
                    
                    # Check if it matches article pattern
                    if re.search(config['article_url_pattern'], url, re.IGNORECASE):
                        if url not in found_links:
                            found_links.add(url)
                            
                            title = extract_title_from_element(element)
                            if not title:
                                title = extract_title_from_url(url)
                            
                            articles.append({
                                'url': url,
                                'title': title,
                                'published': extract_date_from_element(element)
                            })
                            
                            if max_links is not None and len(articles) >= max_links:
                                break
                
                if max_links is not None and len(articles) >= max_links:
                    break
                    
            except Exception as e:
                logger.debug(f"Error with selector '{selector}': {e}")
                continue
        
        logger.info(f"Merolagani: Found {len(articles)} articles from news page")
        
    except Exception as e:
        logger.error(f"Failed to scrape Merolagani news page: {e}")
    
    return articles[:max_links]


def scrape_generic_news_site(config: Dict, max_links: int) -> List[Dict]:
    """
    Scrape articles from generic news sites (nepalipaisa, bikashnews).
    
    Args:
        config: Source configuration
        max_links: Maximum articles to return
        
    Returns:
        List of article dictionaries
    """
    # Try homepage first
    articles = scrape_homepage_articles(config, max_links)
    
    if max_links is not None and len(articles) >= max_links:
        return articles[:max_links]
    
    # Try sitemap as fallback
    if 'sitemap_url' in config:
        logger.info(f"Homepage yielded {len(articles)} articles, trying sitemap...")
        remaining = None if max_links is None else max_links - len(articles)
        sitemap_articles = scrape_sitemap_articles(config, remaining)
        articles.extend(sitemap_articles)
    
    return articles if max_links is None else articles[:max_links]


def scrape_homepage_articles(config: Dict, max_links: int) -> List[Dict]:
    """
    Scrape articles from homepage using CSS selectors.
    
    Args:
        config: Source configuration
        max_links: Maximum articles to return
        
    Returns:
        List of article dictionaries
    """
    articles = []
    
    try:
        response = safe_request(config['domain'])
        if not response:
            return articles
        
        soup = BeautifulSoup(response.content, 'html.parser')
        found_links = set()
        
        for selector in config['homepage_selectors']:
            try:
                elements = soup.select(selector)
                logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                
                for element in elements:
                    href = element.get('href')
                    if not href:
                        continue
                    
                    # Make absolute URL
                    if href.startswith('/'):
                        url = config['domain'] + href
                    elif href.startswith('http'):
                        url = href
                    else:
                        url = urljoin(config['domain'], href)
                    
                    # Check if it matches article pattern
                    if re.search(config['article_url_pattern'], url):
                        if url not in found_links and is_likely_article_link(url):
                            found_links.add(url)
                            
                            title = extract_title_from_element(element)
                            if not title:
                                title = extract_title_from_url(url)
                            
                            articles.append({
                                'url': url,
                                'title': title,
                                'published': extract_date_from_element(element)
                            })
                            
                            if max_links is not None and len(articles) >= max_links:
                                break
                
                if max_links is not None and len(articles) >= max_links:
                    break
                    
            except Exception as e:
                logger.debug(f"Error with selector '{selector}': {e}")
                continue
        
        logger.info(f"Homepage: Found {len(articles)} articles")
        
    except Exception as e:
        logger.error(f"Failed to scrape homepage: {e}")
    
    return articles


def scrape_sitemap_articles(config: Dict, max_links: int) -> List[Dict]:
    """
    Scrape articles from sitemap.xml as fallback.
    
    Args:
        config: Source configuration
        max_links: Maximum articles to return
        
    Returns:
        List of article dictionaries
    """
    articles = []
    
    try:
        sitemap_url = config['domain'] + config['sitemap_url']
        response = safe_request(sitemap_url)
        
        if not response:
            return articles
        
        # Parse XML sitemap
        root = ET.fromstring(response.content)
        
        # Handle different XML namespaces
        namespaces = {
            'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
        }
        
        urls = root.findall('.//sitemap:url', namespaces) or root.findall('.//url')
        
        for url_elem in urls:
            loc_elem = url_elem.find('.//sitemap:loc', namespaces) or url_elem.find('.//loc')
            
            if loc_elem is not None:
                url = loc_elem.text
                
                # Check if it matches article pattern
                if re.search(config['article_url_pattern'], url):
                    if is_likely_article_link(url):
                        title = extract_title_from_url(url)
                        
                        # Try to extract date from sitemap
                        lastmod_elem = url_elem.find('.//sitemap:lastmod', namespaces) or url_elem.find('.//lastmod')
                        published = lastmod_elem.text if lastmod_elem is not None else None
                        
                        articles.append({
                            'url': url,
                            'title': title,
                            'published': published
                        })
                        
                        if len(articles) >= max_links:
                            break
        
        logger.info(f"Sitemap: Found {len(articles)} articles")
        
    except Exception as e:
        logger.error(f"Failed to scrape sitemap: {e}")
    
    return articles


def extract_title_from_element(element) -> str:
    """Extract title from HTML element."""
    if not element:
        return "Unknown Title"
    
    # Try different attributes and text content
    title = (
        element.get('title') or
        element.get('alt') or
        element.text.strip() or
        element.get_text(strip=True)
    )
    
    if title:
        # Clean up title
        title = re.sub(r'\s+', ' ', title)
        title = title.strip()
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(समाचार|News|Article):\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-\s*(Nepali Paisa|Bikash News|Mero Lagani)$', '', title, flags=re.IGNORECASE)
        
        return title[:200]  # Limit length
    
    return "Unknown Title"


def extract_title_from_url(url: str) -> str:
    """Extract title from URL path."""
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if path_parts:
            # Get the last meaningful part
            title_part = path_parts[-1]
            
            # Remove file extensions and IDs
            title_part = re.sub(r'\.(html|php|aspx?)$', '', title_part, flags=re.IGNORECASE)
            title_part = re.sub(r'^\d+[-_]?', '', title_part)  # Remove leading numbers
            
            # Convert to readable format
            title = title_part.replace('-', ' ').replace('_', ' ')
            title = re.sub(r'\s+', ' ', title)
            title = title.strip().title()
            
            if len(title) > 5:
                return title
        
        # Fallback to domain name
        domain = parsed_url.netloc.replace('www.', '')
        return f"Article from {domain}"
        
    except Exception:
        return "Unknown Article"


def extract_date_from_element(element) -> Optional[str]:
    """Extract publication date from HTML element or nearby elements."""
    if not element:
        return None
    
    try:
        # Look for date in various attributes
        for attr in ['datetime', 'data-date', 'data-published']:
            date_val = element.get(attr)
            if date_val:
                return date_val
        
        # Look for date in nearby elements
        parent = element.parent
        if parent:
            date_selectors = [
                '.date', '.published', '.time',
                '[datetime]', '.post-date', '.article-date'
            ]
            
            for selector in date_selectors:
                date_elem = parent.select_one(selector)
                if date_elem:
                    return date_elem.get('datetime') or date_elem.get_text(strip=True)
        
    except Exception as e:
        logger.debug(f"Error extracting date: {e}")
    
    return None


def is_likely_article_link(url: str) -> bool:
    """Check if URL is likely an article (not navigation page)."""
    url_lower = url.lower()
    
    # Exclude navigation pages
    exclude_patterns = [
        '/category/', '/tag/', '/author/', '/page/',
        '/latest', '/popular', '/trending',
        '/search', '/archive', '/sitemap',
        'login', 'register', 'contact', 'about'
    ]
    
    return not any(pattern in url_lower for pattern in exclude_patterns)


def sort_articles_by_freshness(articles: List[Dict]) -> List[Dict]:
    """Sort articles by publication date (newest first)."""
    def parse_date(article):
        published = article.get('published')
        if not published:
            return datetime.min
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y']:
                try:
                    return datetime.strptime(published[:19], fmt)
                except ValueError:
                    continue
            
            # If no format works, return current time (treat as recent)
            return datetime.now()
            
        except Exception:
            return datetime.min
    
    return sorted(articles, key=parse_date, reverse=True)


def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on URL."""
    seen_urls = set()
    unique_articles = []
    
    for article in articles:
        url = article.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles


# CLI interface for testing
def main():
    """CLI interface for testing multi-source scraper."""
    import sys
    
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        source = 'all'
    
    print(f"Testing multi-source scraper with source: {source}")
    print("=" * 60)
    
    try:
        articles = get_multi_source_articles(
            sources=source,
            max_links_per_source=3,
            total_max_links=10
        )
        
        print(f"Found {len(articles)} articles:")
        print()
        
        for i, article in enumerate(articles, 1):
            try:
                print(f"{i}. {article['title']}")
            except UnicodeEncodeError:
                print(f"{i}. [Article with Nepali text]")
            print(f"   Source: {article.get('source_name', 'Unknown')}")
            print(f"   URL: {article['url']}")
            print(f"   Published: {article.get('published', 'Unknown')}")
            print()
        
        print("Multi-source scraping test completed!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
