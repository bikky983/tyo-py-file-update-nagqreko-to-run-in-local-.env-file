#!/usr/bin/env python3
"""
Multi-Source Nepali News Summarizer - Main Pipeline
==================================================

Complete pipeline for scraping, parsing, and summarizing Nepali news from multiple sources:
- nepalipaisa.com
- bikashnews.com  
- merolagani.com

This script:
1. Scrapes latest articles from multiple news sources
2. Extracts clean article content using browser rendering
3. Summarizes articles using DeepSeek LLM API
4. Generates comprehensive reports

Output files:
    - multi_source_links.json: Article URLs and metadata from all sources
    - multi_source_articles.json: Full article content with clean Nepali text
    - multi_source_summaries.json: LLM-generated summaries
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from src.scraper_links import get_multi_source_articles
from src.content_extractor import extract_article_content
from src.article_summarizer import ArticleSummarizer


def main():
    """Main function to run the multi-source Nepali news pipeline."""
    print("=" * 70)
    print("MULTI-SOURCE NEPALI NEWS SUMMARIZER")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Configuration - Time-based filtering for consistency
    sources = ['nepalipaisa', 'bikashnews', 'merolagani']
    max_links_per_source = 6  # Max 6 latest articles per source
    total_max_links = None  # No total limit
    hours_back = 5  # Only scrape news from last 5 hours
    
    try:
        # Step 1: Scrape articles from multiple sources
        print("1. Scraping latest articles from multiple sources...")
        print(f"   Sources: {', '.join(sources)}")
        print(f"   Max per source: {max_links_per_source}")
        print(f"   Total limit: {total_max_links}")
        print(f"   Time filter: Last {hours_back} hours")
        
        links = get_multi_source_articles(
            sources=sources,
            max_links_per_source=max_links_per_source,
            total_max_links=total_max_links,
            hours_back=hours_back
        )
        
        if not links:
            print("   ERROR: No articles found from any source")
            return 1
        
        print(f"   SUCCESS: Found {len(links)} articles")
        
        # Save links
        links_file = "multi_source_links.json"
        with open(links_file, 'w', encoding='utf-8') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        print(f"   Saved links to: {links_file}")
        
        # Show source breakdown
        source_counts = {}
        for link in links:
            source = link.get('source_name', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("   Source breakdown:")
        for source, count in source_counts.items():
            print(f"     - {source}: {count} articles")
        
        print()
        
        # Step 2: Extract article content
        print("2. Extracting article content...")
        parsed_articles = []
        
        for i, link in enumerate(links, 1):
            url = link['url']
            source_name = link.get('source_name', 'Unknown')
            print(f"   Extracting article {i}/{len(links)}: {source_name}")
            print(f"      URL: {url}")
            
            try:
                # Extract article content with intelligent method selection
                article = extract_article_content(url)
                
                # Add source information
                article['source'] = link.get('source', 'unknown')
                article['source_name'] = source_name
                article['scraped_title'] = link.get('title', '')
                article['scraped_published'] = link.get('published')
                
                parsed_articles.append(article)
                
                print(f"      Status: {article['parser_status']}")
                print(f"      Content: {len(article['body_text'])} characters")
                
                # Show extraction method used
                method = article.get('parser_method', 'unknown')
                if method == 'browser_fallback':
                    print(f"      Method: Browser rendering (JavaScript)")
                elif method == 'standard':
                    print(f"      Method: Standard HTTP parsing")
                else:
                    print(f"      Method: {method}")
                
            except Exception as e:
                print(f"      ERROR: {str(e)}")
                # Add failed article with error info
                parsed_articles.append({
                    'url': url,
                    'title': link.get('title', 'Unknown'),
                    'author': None,
                    'published': None,
                    'body_text': '',
                    'parser_status': 'error',
                    'parser_error': str(e),
                    'source': link.get('source', 'unknown'),
                    'source_name': source_name
                })
        
        # Save parsed articles
        articles_file = "multi_source_articles.json"
        with open(articles_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_articles, f, ensure_ascii=False, indent=2)
        print(f"   Saved parsed articles to: {articles_file}")
        print()
        
        # Step 3: Summarize articles (optional)
        print("3. Generating summaries with LLM...")
        
        try:
            # Initialize and run summarizer
            summarizer = ArticleSummarizer(
                input_file=articles_file,
                output_file="multi_source_summaries.json"
            )
            
            summarizer.process_all_articles()
            stats = summarizer.get_summary_stats()
            
            print(f"   SUCCESS: Generated {stats['success_count']}/{stats['total_articles']} summaries")
            print(f"   Saved summaries to: multi_source_summaries.json")
                
        except Exception as e:
            print(f"   WARNING: Summarization failed: {e}")
            print("   Continuing without summaries...")
        
        print()
        
        # Step 4: Generate summary report
        print("=" * 70)
        print("MULTI-SOURCE PIPELINE SUMMARY")
        print("=" * 70)
        
        successful_articles = sum(1 for a in parsed_articles if a['parser_status'] == 'success')
        total_content = sum(len(a['body_text']) for a in parsed_articles)
        
        print(f"Sources scraped: {len(sources)}")
        print(f"Articles found: {len(links)}")
        print(f"Articles parsed successfully: {successful_articles}/{len(parsed_articles)}")
        print(f"Total content extracted: {total_content:,} characters")
        
        print()
        print("Source performance:")
        for source_name, count in source_counts.items():
            source_articles = [a for a in parsed_articles if a.get('source_name') == source_name]
            source_successful = sum(1 for a in source_articles if a['parser_status'] == 'success')
            source_content = sum(len(a['body_text']) for a in source_articles)
            
            print(f"  {source_name}:")
            print(f"    - Articles: {count}")
            print(f"    - Successful: {source_successful}/{count}")
            print(f"    - Content: {source_content:,} characters")
        
        print()
        print("Output files:")
        print(f"  - {links_file}")
        print(f"  - {articles_file}")
        if Path("multi_source_summaries.json").exists():
            print(f"  - multi_source_summaries.json")
        
        print()
        print("SUCCESS: Multi-source pipeline completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\nERROR: Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
