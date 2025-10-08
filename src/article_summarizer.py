"""
Article Summarizer for Nepali News
Reads articles from parsed_articles.json and generates summaries using DeepSeek API.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from loguru import logger

from .llm_api import summarize_text
from .config import validate_api_configuration


class ArticleSummarizer:
    """Handles summarization of news articles using LLM API."""
    
    def __init__(self, input_file: str = "parsed_articles.json", output_file: str = "summarized_articles.json"):
        """
        Initialize the article summarizer.
        
        Args:
            input_file: Path to JSON file containing parsed articles
            output_file: Path to save summarized articles
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
    
    def load_articles(self) -> List[Dict[str, Any]]:
        """
        Load articles from the input JSON file.
        
        Returns:
            List of article dictionaries
        
        Raises:
            FileNotFoundError: If input file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            logger.info(f"Loaded {len(articles)} articles from {self.input_file}")
            return articles
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.input_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading articles: {e}")
            raise
    
    def summarize_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize a single article using the LLM API.
        
        Args:
            article: Article dictionary with 'title' and 'body_text'
        
        Returns:
            Article dictionary with added summary information
        """
        # Extract article content
        title = article.get('title', '')
        body_text = article.get('body_text', '')
        url = article.get('url', '')
        
        if not body_text or not body_text.strip():
            logger.warning(f"Empty body text for article: {url}")
            return {
                **article,
                'summary': '',
                'summary_status': 'error',
                'summary_error': 'Empty body text',
                'summary_metadata': {},
                'summarized_at': datetime.now().isoformat()
            }
        
        logger.info(f"Summarizing article: {title[:50]}...")
        
        # Call LLM API for summarization
        result = summarize_text(
            text=body_text,
            title=title,
            language="ne"
        )
        
        # Prepare the enhanced article with summary
        summarized_article = {
            **article,
            'summary': result.get('summary', ''),
            'summary_status': 'success' if result.get('success') else 'error',
            'summary_error': result.get('error'),
            'summary_metadata': result.get('metadata', {}),
            'summarized_at': datetime.now().isoformat()
        }
        
        if result.get('success'):
            logger.info(f"✓ Successfully summarized: {title[:50]}...")
            logger.info(f"  Summary: {result['summary'][:100]}...")
            self.success_count += 1
        else:
            logger.error(f"✗ Failed to summarize: {title[:50]}...")
            logger.error(f"  Error: {result.get('error')}")
            self.error_count += 1
        
        self.processed_count += 1
        return summarized_article
    
    def save_summaries(self, summarized_articles: List[Dict[str, Any]]) -> None:
        """
        Save summarized articles to output JSON file.
        
        Args:
            summarized_articles: List of articles with summaries
        """
        try:
            # Create backup if output file exists
            if self.output_file.exists():
                backup_file = self.output_file.with_suffix('.backup.json')
                self.output_file.rename(backup_file)
                logger.info(f"Created backup: {backup_file}")
            
            # Filter out articles with errors (empty summaries or failed extraction)
            valid_summaries = [
                article for article in summarized_articles 
                if article.get('summary') and article.get('summary').strip() and 
                article.get('summary_status') == 'success'
            ]
            
            filtered_count = len(summarized_articles) - len(valid_summaries)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} articles with errors (empty or failed)")
            
            # Save only valid summaries
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(valid_summaries, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(valid_summaries)} valid summarized articles to {self.output_file}")
            
        except Exception as e:
            logger.error(f"Error saving summaries: {e}")
            raise
    
    def process_all_articles(self) -> None:
        """
        Process all articles from input file and save summaries.
        """
        # Validate API configuration
        is_valid, error_msg = validate_api_configuration()
        if not is_valid:
            logger.error(f"API configuration error: {error_msg}")
            raise RuntimeError(f"API configuration error: {error_msg}")
        
        logger.info("Starting article summarization process...")
        
        # Load articles
        articles = self.load_articles()
        
        if not articles:
            logger.warning("No articles found to process")
            return
        
        # Process each article
        summarized_articles = []
        
        for i, article in enumerate(articles, 1):
            logger.info(f"Processing article {i}/{len(articles)}")
            
            try:
                summarized_article = self.summarize_article(article)
                summarized_articles.append(summarized_article)
                
                # Add small delay between requests to be respectful to API
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing article {i}: {e}")
                # Add article with error status
                error_article = {
                    **article,
                    'summary': '',
                    'summary_status': 'error',
                    'summary_error': str(e),
                    'summary_metadata': {},
                    'summarized_at': datetime.now().isoformat()
                }
                summarized_articles.append(error_article)
                self.error_count += 1
                self.processed_count += 1
        
        # Save results
        self.save_summaries(summarized_articles)
        
        # Print summary
        logger.info("=" * 50)
        logger.info("SUMMARIZATION COMPLETE")
        logger.info(f"Total articles processed: {self.processed_count}")
        logger.info(f"Successfully summarized: {self.success_count}")
        logger.info(f"Errors: {self.error_count}")
        logger.info(f"Success rate: {(self.success_count/self.processed_count)*100:.1f}%")
        logger.info(f"Results saved to: {self.output_file}")
        logger.info("=" * 50)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the summarization process.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / self.processed_count * 100) if self.processed_count > 0 else 0,
            'input_file': str(self.input_file),
            'output_file': str(self.output_file)
        }


def main():
    """Main function to run article summarization."""
    import sys
    
    # Setup logging
    logger.add("logs/article_summarizer.log", rotation="10 MB", level="INFO")
    
    # Get file paths from command line or use defaults
    input_file = sys.argv[1] if len(sys.argv) > 1 else "parsed_articles.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "summarized_articles.json"
    
    try:
        # Create summarizer and process articles
        summarizer = ArticleSummarizer(input_file, output_file)
        summarizer.process_all_articles()
        
        # Print final stats
        stats = summarizer.get_summary_stats()
        print("\nSummarization Results:")
        print(f"  Processed: {stats['processed_count']} articles")
        print(f"  Success: {stats['success_count']} articles")
        print(f"  Errors: {stats['error_count']} articles")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
        print(f"  Output: {stats['output_file']}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
