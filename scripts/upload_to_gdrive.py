#!/usr/bin/env python3
"""
Google Drive Upload Script for Nepali News Posts
================================================

This script uploads generated news post images to Google Drive using Rclone.
It creates organized folders by date and time slot.
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path


def setup_rclone_config():
    """Set up Rclone configuration from environment variable."""
    rclone_config = os.getenv('RCLONE_CONFIG')
    if not rclone_config:
        print("ERROR: RCLONE_CONFIG environment variable not set")
        return False
    
    # Create rclone config directory
    config_dir = Path.home() / '.config' / 'rclone'
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Write config file
    config_file = config_dir / 'rclone.conf'
    with open(config_file, 'w') as f:
        f.write(rclone_config)
    
    print(f"✅ Rclone config written to: {config_file}")
    return True


def get_time_slot():
    """Determine current time slot based on Nepal time."""
    # Get current hour in Nepal time (UTC+5:45)
    import pytz
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    nepal_time = datetime.now(nepal_tz)
    hour = nepal_time.hour
    
    if 5 <= hour < 11:
        return 'morning'
    elif 11 <= hour < 16:
        return 'afternoon'
    else:
        return 'evening'


def upload_images_to_gdrive(output_dir='output', remote_name='gdrive'):
    """Upload images to Google Drive with organized folder structure."""
    
    # Check if output directory exists
    if not os.path.exists(output_dir):
        print(f"ERROR: Output directory '{output_dir}' not found")
        return False
    
    # Get PNG files (sort for consistent ordering)
    png_files = sorted(list(Path(output_dir).glob('*.png')))
    if not png_files:
        print(f"WARNING: No PNG files found in '{output_dir}'")
        return True
    
    print(f"📁 Found {len(png_files)} images to upload:")
    for i, png_file in enumerate(png_files, 1):
        print(f"   {i}. {png_file.name}")
    
    # Create folder structure: NepaliNewsPosts/YYYY-MM-DD/morning|afternoon|evening/
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    nepal_time = datetime.now(nepal_tz)
    date_str = nepal_time.strftime('%Y-%m-%d')
    time_slot = get_time_slot()
    
    remote_folder = f"NepaliNewsPosts/{date_str}/{time_slot}"
    
    print(f"📤 Uploading to: {remote_name}:{remote_folder}")
    
    try:
        # Create remote directory
        cmd_mkdir = ['rclone', 'mkdir', f'{remote_name}:{remote_folder}']
        result = subprocess.run(cmd_mkdir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"WARNING: Could not create directory: {result.stderr}")
        
        # Upload all PNG files
        success_count = 0
        for png_file in png_files:
            print(f"  Uploading: {png_file.name}")
            
            cmd_copy = [
                'rclone', 'copy', 
                str(png_file), 
                f'{remote_name}:{remote_folder}/',
                '--progress'
            ]
            
            result = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✅ Success: {png_file.name}")
                success_count += 1
            else:
                print(f"    ❌ Failed: {png_file.name}")
                print(f"    Error: {result.stderr}")
        
        print(f"\n📊 Upload Summary:")
        print(f"  Total files: {len(png_files)}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {len(png_files) - success_count}")
        print(f"  Google Drive folder: {remote_folder}")
        
        # Get shareable link to the folder
        try:
            cmd_link = ['rclone', 'link', f'{remote_name}:{remote_folder}']
            result = subprocess.run(cmd_link, capture_output=True, text=True)
            if result.returncode == 0:
                link = result.stdout.strip()
                print(f"  📎 Shareable link: {link}")
        except:
            pass
        
        return success_count == len(png_files)
        
    except Exception as e:
        print(f"ERROR: Upload failed: {e}")
        return False


def main():
    """Main function."""
    print("🚀 Starting Google Drive Upload")
    print("=" * 50)
    
    # Setup rclone config
    if not setup_rclone_config():
        sys.exit(1)
    
    # Test rclone connection
    print("🔍 Testing rclone connection...")
    try:
        result = subprocess.run(['rclone', 'about', 'gdrive:'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Rclone connection successful")
        else:
            print(f"❌ Rclone connection failed: {result.stderr}")
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print("❌ Rclone connection timeout")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Rclone test failed: {e}")
        sys.exit(1)
    
    # Upload images
    success = upload_images_to_gdrive()
    
    if success:
        print("\n🎉 All images uploaded successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some uploads failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
