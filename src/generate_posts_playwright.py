#!/usr/bin/env python3
"""
Generate social media posts using Playwright (browser rendering)
This properly handles Nepali Devanagari text including complex conjuncts
"""

import argparse
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import datetime


def create_html_template(summaries, show_numbers=True, start_index=1):
    """Create HTML template with Nepali summaries."""
    
    # Build summary HTML
    summary_html = ""
    for i, summary in enumerate(summaries, start_index):
        summary_text = summary.get('summary', '')
        if show_numbers:
            summary_html += f'<div class="summary">{i}. {summary_text}</div>\n'
        else:
            summary_html += f'<div class="summary">{summary_text}</div>\n'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600&display=swap');
            
            body {{
                margin: 0;
                padding: 0;
                width: 1080px;
                height: 1920px;
                background-image: url('file:///{Path('background.png').absolute().as_posix()}');
                background-size: cover;
                background-position: center;
                font-family: 'Noto Sans Devanagari', sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .container {{
                width: 90%;
                max-width: 950px;
                padding: 60px 40px;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            
            .summary {{
                font-size: 32px;
                line-height: 1.6;
                color: #1a1a1a;
                margin-bottom: 40px;
                padding-bottom: 30px;
                border-bottom: 2px solid #e0e0e0;
            }}
            
            .summary:last-child {{
                border-bottom: none;
                margin-bottom: 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {summary_html}
        </div>
    </body>
    </html>
    """
    return html


def generate_post_with_playwright(summaries, output_path, config, start_index=1):
    """Generate post using Playwright browser rendering."""
    
    html = create_html_template(summaries, not config.get('no_number', False), start_index)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1080, 'height': 1920})
        
        page.set_content(html)
        
        # Wait for fonts to load
        page.wait_for_timeout(2000)
        
        page.screenshot(path=str(output_path), full_page=True)
        
        browser.close()
    
    return True


def generate_multiple_posts(summaries, output_dir, config):
    """Generate multiple posts if summaries don't fit in one post."""
    
    # Maximum summaries per post (to ensure readability)
    max_per_post = config.get('max_per_post', 6)
    
    # Split summaries into chunks
    total_summaries = len(summaries)
    num_posts = (total_summaries + max_per_post - 1) // max_per_post  # Ceiling division
    
    print(f"INFO: Generating {num_posts} post(s) for {total_summaries} summaries...")
    print(f"INFO: Max {max_per_post} summaries per post")
    
    generated_posts = []
    
    with sync_playwright() as p:
        print("INFO: Launching browser for rendering...")
        browser = p.chromium.launch()
        
        for post_num in range(num_posts):
            start_idx = post_num * max_per_post
            end_idx = min(start_idx + max_per_post, total_summaries)
            chunk = summaries[start_idx:end_idx]
            
            # Generate output filename
            if num_posts == 1:
                output_path = output_dir / "combined_news_post.png"
            else:
                output_path = output_dir / f"combined_news_post_{post_num + 1}.png"
            
            print(f"INFO: Generating post {post_num + 1}/{num_posts} with summaries {start_idx + 1}-{end_idx}...")
            
            # Create HTML
            html = create_html_template(chunk, not config.get('no_number', False), start_idx + 1)
            
            # Render
            page = browser.new_page(viewport={'width': 1080, 'height': 1920})
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.screenshot(path=str(output_path), full_page=True)
            page.close()
            
            print(f"SUCCESS: Generated {output_path.name}")
            generated_posts.append(str(output_path))
        
        browser.close()
    
    return generated_posts


def main():
    parser = argparse.ArgumentParser(description="Generate posts with Playwright (perfect Nepali rendering)")
    parser.add_argument('--input', default='multi_source_summaries.json')
    parser.add_argument('--output-dir', default='output')
    parser.add_argument('--no-number', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--max-per-post', type=int, default=6, help='Maximum summaries per post')
    
    args = parser.parse_args()
    
    # Load summaries
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        summaries = json.load(f)
    
    print(f"INFO: Loaded {len(summaries)} summaries")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate posts (multiple if needed)
    config = {
        'no_number': args.no_number,
        'max_per_post': args.max_per_post
    }
    
    generated_posts = generate_multiple_posts(summaries, output_dir, config)
    
    print(f"\nSUCCESS: Generated {len(generated_posts)} post(s)")
    for post in generated_posts:
        print(f"   - {post}")
    print("\nThe Nepali text renders PERFECTLY with all conjuncts!")


if __name__ == '__main__':
    main()
