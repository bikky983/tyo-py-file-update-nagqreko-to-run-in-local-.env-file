#!/usr/bin/env python3
"""
Multi-Source Summary Post Generator

Generates social media posts with 4-5 summaries per image from multi_source_summaries.json.
Supports both Nepali (Devanagari) and English text with proper font rendering.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import urllib.request
from PIL import Image, ImageDraw, ImageFont
import textwrap
import math


class PostGenerator:
    """Generates social media posts with multiple summaries per image."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.fonts = {}
        self.canvas_size = None
        self.background_image = None
        
    def download_font(self, url: str, filename: str, fonts_dir: Path) -> bool:
        """Download a font file from URL."""
        try:
            import urllib.request
            font_path = fonts_dir / filename
            print(f"INFO: Downloading {filename}...")
            urllib.request.urlretrieve(url, font_path)
            print(f"SUCCESS: Downloaded {filename}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to download {filename}: {e}")
            return False
    
    def setup_fonts(self) -> bool:
        """Setup fonts for Nepali and English text rendering."""
        fonts_dir = Path("fonts")
        fonts_dir.mkdir(exist_ok=True)
        
        # Direct download URLs for fonts - using Preeti for Nepali
        font_files = {
            'english': {
                'filename': 'NotoSans-Regular.ttf',
                'url': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf'
            },
            'nepali': {
                'filename': 'preeti.ttf', 
                'url': 'https://github.com/nepali-fonts/preeti/raw/master/preeti.ttf'
            }
        }
        
        # Check and download missing fonts
        for lang, font_info in font_files.items():
            filename = font_info['filename']
            font_path = fonts_dir / filename
            
            if not font_path.exists():
                print(f"INFO: Font {filename} not found, attempting to download...")
                if not self.download_font(font_info['url'], filename, fonts_dir):
                    print(f"WARNING: Could not download {filename}")
                    if lang == 'nepali':
                        print("WARNING: Nepali text may not render correctly without proper fonts")
            else:
                print(f"INFO: Font {filename} already available")
        
        return True
    
    def load_font(self, language: str, size: int) -> ImageFont.FreeTypeFont:
        """Load appropriate font for the given language and size."""
        fonts_dir = Path("fonts")
        
        if language == "ne":  # Nepali - try system Devanagari fonts first (better rendering)
            # Try Windows system fonts first - they have better Devanagari support
            devanagari_fonts = [
                "C:/Windows/Fonts/mangal.ttf",      # Windows Devanagari font - BEST for complex conjuncts
                "C:/Windows/Fonts/Nirmala.ttf",     # Windows 10 Devanagari font
                "C:/Windows/Fonts/NirmalaB.ttf",    # Nirmala Bold
                "C:/Windows/Fonts/kokila.ttf",      # Another Devanagari font
                "C:/Windows/Fonts/utsaah.ttf",      # Devanagari font
            ]
            
            for font_path in devanagari_fonts:
                if Path(font_path).exists():
                    try:
                        font = ImageFont.truetype(font_path, size)
                        print(f"INFO: Using Windows Devanagari font: {Path(font_path).name}")
                        return font
                    except Exception as e:
                        print(f"WARNING: Failed to load {font_path}: {e}")
                        continue
            
            # Try Preeti font
            preeti_path = fonts_dir / "preeti.ttf"
            if preeti_path.exists():
                try:
                    font = ImageFont.truetype(str(preeti_path), size)
                    print(f"INFO: Using Preeti font for Nepali text")
                    return font
                except Exception as e:
                    print(f"ERROR: Failed to load Preeti font: {e}")
            
            # Fallback to Noto Devanagari
            noto_path = fonts_dir / "NotoSansDevanagari-Regular.ttf"
            if noto_path.exists():
                try:
                    font = ImageFont.truetype(str(noto_path), size)
                    print(f"INFO: Using Noto Devanagari font for Nepali text")
                    return font
                except Exception as e:
                    print(f"ERROR: Failed to load Noto Devanagari font: {e}")
            
            print(f"ERROR: No Devanagari fonts found! Nepali text will not render correctly.")
            print(f"SUGGESTION: Install Mangal font on Windows or place preeti.ttf in fonts/ directory")
            return ImageFont.load_default()
            
        else:  # English or default
            font_path = fonts_dir / "NotoSans-Regular.ttf"
            try:
                return ImageFont.truetype(str(font_path), size)
            except Exception as e:
                # Fallback for English
                fallback_fonts = [
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/calibri.ttf", 
                    "C:/Windows/Fonts/segoeui.ttf",
                ]
                
                for fallback in fallback_fonts:
                    try:
                        return ImageFont.truetype(fallback, size)
                    except:
                        continue
                
                return ImageFont.load_default()
    
    def find_background_image(self) -> Optional[Path]:
        """Find background image with various extensions."""
        # Try different background image formats
        possible_names = [
            self.config['background'],  # User specified
            'background.jpg',
            'background.jpeg', 
            'background.png',
            'background.webp'
        ]
        
        for name in possible_names:
            bg_path = Path(name)
            if bg_path.exists():
                return bg_path
        
        return None
    
    def setup_canvas_and_background(self) -> bool:
        """Setup canvas size and load background image."""
        # Parse canvas size from config
        size_str = self.config['size']
        if 'x' in size_str:
            width, height = map(int, size_str.split('x'))
        else:
            width = height = int(size_str)
        
        # For 9:16 aspect ratio posts (Facebook/Instagram Stories)
        if width == height:  # If square specified, convert to 9:16
            height = int(width * 16 / 9)
        
        self.canvas_size = (width, height)
        
        # Find and load background image
        bg_path = self.find_background_image()
        if not bg_path:
            print(f"ERROR: No background image found. Tried:")
            print(f"  - {self.config['background']}")
            print(f"  - background.jpg")
            print(f"  - background.jpeg") 
            print(f"  - background.png")
            print(f"  - background.webp")
            return False
        
        try:
            self.background_image = Image.open(bg_path).convert('RGBA')
            print(f"SUCCESS: Loaded background: {bg_path} ({self.background_image.size})")
            return True
        except Exception as e:
            print(f"ERROR: Error loading background image: {e}")
            return False
    
    def get_content_area(self) -> Tuple[int, int, int, int]:
        """Calculate content area coordinates (left, top, right, bottom)."""
        width, height = self.canvas_size
        
        top_margin = int(height * self.config['top_margin'])
        bottom_margin = int(height * self.config['bottom_margin'])
        side_margin = int(width * self.config['side_margin'])
        
        left = side_margin
        top = top_margin
        right = width - side_margin
        bottom = height - bottom_margin
        
        return left, top, right, bottom
    
    def calculate_luminance(self, image: Image.Image, area: Tuple[int, int, int, int]) -> float:
        """Calculate average luminance of image area to determine text color."""
        left, top, right, bottom = area
        crop = image.crop((left, top, right, bottom))
        crop = crop.convert('L')  # Convert to grayscale
        
        # Calculate average brightness
        pixels = list(crop.getdata())
        return sum(pixels) / len(pixels) / 255.0
    
    def wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wrap text to fit within max_width preserving original text exactly."""
        # Preserve the exact text - no modifications
        words = text.split(' ')  # Split only on spaces to preserve punctuation
        lines = []
        current_line = []
        
        for word in words:
            # Test if adding this word would exceed the width
            test_line = ' '.join(current_line + [word])
            
            try:
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except Exception as e:
                # Fallback if getbbox fails - be more conservative
                text_width = len(test_line) * 25  # Slightly larger estimate for safety
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Even single word is too long - just add it anyway to preserve text
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Text wrapped successfully - no debug output to avoid encoding issues
        
        return lines
    
    def calculate_text_height(self, lines: List[str], font: ImageFont.FreeTypeFont, line_spacing: float = 1.2) -> int:
        """Calculate total height needed for text lines."""
        if not lines:
            return 0
        
        bbox = font.getbbox('Ag')  # Use characters with ascenders and descenders
        line_height = int((bbox[3] - bbox[1]) * line_spacing)
        return len(lines) * line_height
    
    def truncate_text_if_needed(self, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_height: int) -> Tuple[str, bool]:
        """Truncate text if it doesn't fit in the available space."""
        lines = self.wrap_text(text, font, max_width)
        text_height = self.calculate_text_height(lines, font, 1.3)
        
        if text_height <= max_height:
            return text, False
        
        # Calculate how many lines we can fit
        try:
            bbox = font.getbbox('Ag')
            line_height = int((bbox[3] - bbox[1]) * 1.3)
        except:
            line_height = int(font.size * 1.3)
            
        max_lines = max(1, max_height // line_height)
        
        if max_lines <= 0:
            return "...", True
        
        # Truncate to fit
        truncated_lines = lines[:max_lines]
        if len(truncated_lines) < len(lines):
            # Add ellipsis to last line if we had to truncate
            if truncated_lines:
                last_line = truncated_lines[-1]
                ellipsis = "..."
                
                # Try to fit ellipsis
                while last_line:
                    test_text = last_line + ellipsis
                    try:
                        bbox = font.getbbox(test_text)
                        if bbox[2] - bbox[0] <= max_width:
                            truncated_lines[-1] = test_text
                            break
                    except:
                        if len(test_text) * 20 <= max_width:  # Rough estimate
                            truncated_lines[-1] = test_text
                            break
                    
                    # Remove last word and try again
                    words = last_line.split()
                    if len(words) <= 1:
                        truncated_lines[-1] = ellipsis
                        break
                    words = words[:-1]
                    last_line = ' '.join(words)
        
        return '\n'.join(truncated_lines), True
    
    def draw_summary_block(self, draw: ImageDraw.Draw, summary: Dict, block_area: Tuple[int, int, int, int], 
                          index: int, text_color: str, show_numbers: bool) -> Dict:
        """Draw a single summary block and return metadata."""
        left, top, right, bottom = block_area
        content_width = right - left
        content_height = bottom - top
        
        # Get exact summary text from JSON - no modifications
        original_summary = summary.get('summary', '')
        language = summary.get('summary_metadata', {}).get('language', 'en')
        
        # Load fonts - larger for better mobile readability
        summary_font_size = 36  # Larger size for better readability on mobile
        
        summary_font = self.load_font(language, summary_font_size)
        
        current_y = top
        
        # Prepare final text with numbering if requested
        if show_numbers:
            summary_text = f"{index}. {original_summary}"
        else:
            summary_text = original_summary
        
        # Calculate available space for summary
        available_height = bottom - current_y
        
        # Try to fit text, scale down if necessary
        min_font_size = 20  # Increased minimum for better readability
        truncated = False
        
        while summary_font_size >= min_font_size:
            summary_font = self.load_font(language, summary_font_size)
            
            # Check if text fits
            lines = self.wrap_text(summary_text, summary_font, content_width)
            text_height = self.calculate_text_height(lines, summary_font, 1.3)  # Better line spacing
            
            if text_height <= available_height:
                break
            
            # Reduce font size more gradually
            summary_font_size -= 1
        
        # If still doesn't fit, truncate
        if summary_font_size < min_font_size:
            summary_font_size = min_font_size
            summary_font = self.load_font(language, summary_font_size)
            summary_text, truncated = self.truncate_text_if_needed(
                summary_text, summary_font, content_width, available_height
            )
        
        # Draw the summary text with better visibility
        lines = self.wrap_text(summary_text, summary_font, content_width)
        
        try:
            bbox = summary_font.getbbox('Ag')
            line_height = int((bbox[3] - bbox[1]) * 1.3)  # Good line spacing
        except:
            # Fallback line height calculation
            line_height = int(summary_font_size * 1.3)
        
        for line in lines:
            if line.strip():  # Only draw non-empty lines
                # Draw text with proper Unicode handling
                try:
                    # Ensure text is properly encoded
                    text_to_draw = line.encode('utf-8').decode('utf-8')
                    draw.text((left, current_y), text_to_draw, font=summary_font, fill=text_color)
                except Exception as e:
                    print(f"ERROR: Failed to draw line '{line}': {e}")
                    # Fallback - try character by character
                    try:
                        draw.text((left, current_y), line, font=summary_font, fill=text_color)
                    except:
                        print(f"ERROR: Could not draw text at all")
            current_y += line_height
        
        return {
            'truncated': truncated,
            'font_size_used': summary_font_size,
            'lines_used': len(lines)
        }
    
    def generate_post_image(self, summaries: List[Dict], output_path: Path, post_index: int) -> Dict:
        """Generate a single post image with multiple summaries."""
        # Create canvas
        canvas = Image.new('RGBA', self.canvas_size, (255, 255, 255, 255))
        
        # Scale and place background image
        bg_scaled = self.background_image.copy()
        
        # Scale background to cover canvas while maintaining aspect ratio
        canvas_ratio = self.canvas_size[0] / self.canvas_size[1]
        bg_ratio = bg_scaled.size[0] / bg_scaled.size[1]
        
        if bg_ratio > canvas_ratio:
            # Background is wider, scale by height
            new_height = self.canvas_size[1]
            new_width = int(new_height * bg_ratio)
        else:
            # Background is taller, scale by width
            new_width = self.canvas_size[0]
            new_height = int(new_width / bg_ratio)
        
        bg_scaled = bg_scaled.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center the background
        bg_x = (self.canvas_size[0] - new_width) // 2
        bg_y = (self.canvas_size[1] - new_height) // 2
        canvas.paste(bg_scaled, (bg_x, bg_y))
        
        # Get content area
        content_left, content_top, content_right, content_bottom = self.get_content_area()
        
        # Use black text on the background image directly (no dark panel)
        text_color = 'black'  # Black text for better visibility on light backgrounds
        draw = ImageDraw.Draw(canvas)
        
        # Calculate space for each summary block
        content_height = content_bottom - content_top
        num_summaries = len(summaries)
        
        # Reserve space for gaps between blocks (better spacing for readability)
        min_gap = int(self.canvas_size[1] * 0.05)  # Increased gap for better separation
        total_gap_space = (num_summaries - 1) * min_gap
        available_height = content_height - total_gap_space
        block_height = available_height // num_summaries
        
        # Generate each summary block
        post_metadata = {
            'summaries': [],
            'truncated_entries': [],
            'font_sizes_used': [],
            'text_color': text_color
        }
        
        current_y = content_top
        
        for i, summary in enumerate(summaries, 1):
            block_top = current_y
            block_bottom = current_y + block_height
            
            block_metadata = self.draw_summary_block(
                draw, summary, 
                (content_left, block_top, content_right, block_bottom),
                i, text_color, not self.config.get('no_number', False)
            )
            
            post_metadata['summaries'].append({
                'url': summary.get('url', ''),
                'title': summary.get('title', ''),
                'source': summary.get('source_name', ''),
                'language': summary.get('summary_metadata', {}).get('language', 'en'),
                **block_metadata
            })
            
            if block_metadata['truncated']:
                post_metadata['truncated_entries'].append(i)
            
            post_metadata['font_sizes_used'].append(block_metadata['font_size_used'])
            
            current_y = block_bottom + min_gap
        
        # Save the image with proper settings
        try:
            canvas_rgb = Image.new('RGB', self.canvas_size, (255, 255, 255))
            canvas_rgb.paste(canvas, mask=canvas.split()[-1])  # Use alpha channel as mask
            canvas_rgb.save(output_path, 'PNG', optimize=False, quality=95)
            print(f"INFO: Successfully saved image to {output_path}")
        except Exception as e:
            print(f"ERROR: Failed to save image: {e}")
            # Try alternative save method
            try:
                canvas.save(output_path, 'PNG')
                print(f"INFO: Saved with alternative method to {output_path}")
            except Exception as e2:
                print(f"ERROR: Alternative save also failed: {e2}")
                raise
        
        return post_metadata
    
    def generate_posts(self, summaries: List[Dict]) -> Dict:
        """Generate a single combined post with all summaries."""
        output_dir = Path(self.config['output'])
        output_dir.mkdir(exist_ok=True)
        
        manifest = {
            'generated_at': None,
            'config': self.config,
            'posts': []
        }
        
        # Use all summaries in a single post
        filename = "combined_news_post.png"
        output_path = output_dir / filename
        
        # Skip if file exists and not forcing
        if output_path.exists() and not self.config.get('force', False):
            print(f"SKIP: Skipping {filename} (already exists)")
            manifest['posts'].append({
                'filename': filename,
                'index': 1,
                'skipped': True,
                'summaries_count': len(summaries)
            })
        else:
            print(f"INFO: Generating single combined post with {len(summaries)} summaries...")
            print(f"INFO: Generating {filename}...")
            
            # Generate the post with all summaries
            post_metadata = self.generate_post_image(summaries, output_path, 1)
            
            # Add to manifest
            manifest['posts'].append({
                'filename': filename,
                'index': 1,
                'summaries_count': len(summaries),
                'size': f"{self.canvas_size[0]}x{self.canvas_size[1]}",
                'margins': {
                    'top': self.config['top_margin'],
                    'bottom': self.config['bottom_margin'],
                    'side': self.config['side_margin']
                },
                **post_metadata
            })
            
            print(f"SUCCESS: Generated {filename}")
        
        # Save manifest
        import datetime
        manifest['generated_at'] = datetime.datetime.now().isoformat()
        
        manifest_path = output_dir / 'manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"INFO: Saved manifest to {manifest_path}")
        return manifest


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate social media posts with multiple summaries per image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.generate_multi_summary_posts
  python -m src.generate_multi_summary_posts --size 1080x1920 --force
  python -m src.generate_multi_summary_posts --no-number --force
        """
    )
    
    parser.add_argument('--input', default='multi_source_summaries.json',
                       help='Input JSON file with summaries (default: multi_source_summaries.json)')
    parser.add_argument('--background', default='background.jpg',
                       help='Background image file (default: auto-detect background.jpg/jpeg/png/webp)')
    parser.add_argument('--out', '--output', dest='output', default='output',
                       help='Output directory (default: output)')
    parser.add_argument('--per-post', type=int, default=4,
                       help='Number of summaries per post (default: 4)')
    parser.add_argument('--size', default='1080x1920',
                       help='Canvas size WxH or single number for square (default: 1080x1920 for 9:16)')
    parser.add_argument('--top-margin', type=float, default=0.10,
                       help='Top margin ratio (default: 0.10)')
    parser.add_argument('--bottom-margin', type=float, default=0.07,
                       help='Bottom margin ratio (default: 0.07)')
    parser.add_argument('--side-margin', type=float, default=0.06,
                       help='Side margin ratio (default: 0.06)')
    parser.add_argument('--no-number', action='store_true',
                       help='Disable numbering of summaries')
    parser.add_argument('--force', action='store_true',
                       help='Overwrite existing files')
    
    args = parser.parse_args()
    
    # Convert args to config dict
    config = {
        'input': args.input,
        'background': args.background,
        'output': args.output,
        'per_post': args.per_post,
        'size': args.size,
        'top_margin': args.top_margin,
        'bottom_margin': args.bottom_margin,
        'side_margin': args.side_margin,
        'no_number': args.no_number,
        'force': args.force
    }
    
    print("Multi-Source Summary Post Generator")
    print("=" * 50)
    
    # Check input file
    input_path = Path(config['input'])
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        print(f"Please ensure {input_path} exists in the current directory.")
        sys.exit(1)
    
    # Load summaries with proper UTF-8 encoding
    try:
        with open(input_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM if present
            summaries = json.load(f)
        print(f"INFO: Loaded {len(summaries)} summaries from {input_path}")
        
        # Verify first summary text
        if summaries:
            first_summary = summaries[0].get('summary', '')
            print(f"INFO: First summary length: {len(first_summary)} characters")
    except Exception as e:
        print(f"ERROR: Error loading summaries: {e}")
        sys.exit(1)
    
    # Initialize generator
    generator = PostGenerator(config)
    
    # Setup fonts
    if not generator.setup_fonts():
        sys.exit(1)
    
    # Setup canvas and background
    if not generator.setup_canvas_and_background():
        sys.exit(1)
    
    # Generate posts
    try:
        manifest = generator.generate_posts(summaries)
        
        print("\nSUCCESS: Post generation completed!")
        print(f"INFO: Output directory: {config['output']}")
        print(f"INFO: Generated {len([p for p in manifest['posts'] if not p.get('skipped', False)])} posts")
        
        # Show truncation warnings if any
        truncated_posts = [p for p in manifest['posts'] if p.get('truncated_entries')]
        if truncated_posts:
            print(f"WARNING: {len(truncated_posts)} posts had truncated text due to space constraints")
        
    except Exception as e:
        print(f"ERROR: Error generating posts: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
