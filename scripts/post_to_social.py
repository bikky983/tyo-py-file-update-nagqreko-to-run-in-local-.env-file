#!/usr/bin/env python3
"""
Social Media Auto-Poster for Nepali News
========================================

This script automatically posts generated news images to:
- Facebook Page
- Instagram Business Account

Features:
- Posts multiple images as carousel/album
- No titles/captions - just images
- Handles authentication via environment variables
- Supports both Facebook Graph API and Instagram Basic Display API
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SocialMediaPoster:
    """Handles posting to Facebook and Instagram."""
    
    def __init__(self):
        """Initialize with API credentials from environment variables."""
        # Facebook credentials
        self.fb_access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.fb_page_id = os.getenv('FACEBOOK_PAGE_ID')
        
        # Instagram credentials  
        self.ig_access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.ig_user_id = os.getenv('INSTAGRAM_USER_ID')
        
        # API endpoints
        self.fb_api_base = "https://graph.facebook.com/v18.0"
        self.ig_api_base = "https://graph.facebook.com/v18.0"
        
        # Validate credentials
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate that required credentials are present."""
        missing_creds = []
        
        if not self.fb_access_token:
            missing_creds.append('FACEBOOK_ACCESS_TOKEN')
        if not self.fb_page_id:
            missing_creds.append('FACEBOOK_PAGE_ID')
        if not self.ig_access_token:
            missing_creds.append('INSTAGRAM_ACCESS_TOKEN')
        if not self.ig_user_id:
            missing_creds.append('INSTAGRAM_USER_ID')
        
        if missing_creds:
            logger.error(f"Missing required environment variables: {', '.join(missing_creds)}")
            logger.error("Please set these environment variables before running the script.")
            sys.exit(1)
        
        logger.info("✅ All social media credentials found")
    
    def get_image_files(self, output_dir: str = 'output') -> List[Path]:
        """Get all PNG image files from output directory."""
        output_path = Path(output_dir)
        
        if not output_path.exists():
            logger.error(f"Output directory '{output_dir}' not found")
            return []
        
        # Get all PNG files
        image_files = list(output_path.glob('*.png'))
        
        if not image_files:
            logger.warning(f"No PNG files found in '{output_dir}'")
            return []
        
        # Sort by filename for consistent ordering
        image_files.sort()
        logger.info(f"Found {len(image_files)} image files: {[f.name for f in image_files]}")
        
        return image_files
    
    def upload_image_to_facebook(self, image_path: Path) -> Optional[str]:
        """Upload image to Facebook and return media ID."""
        try:
            url = f"{self.fb_api_base}/{self.fb_page_id}/photos"
            
            with open(image_path, 'rb') as image_file:
                files = {'source': image_file}
                data = {
                    'access_token': self.fb_access_token,
                    'published': 'false'  # Don't publish immediately, just upload
                }
                
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()
                
                result = response.json()
                media_id = result.get('id')
                
                if media_id:
                    logger.info(f"✅ Uploaded {image_path.name} to Facebook (ID: {media_id})")
                    return media_id
                else:
                    logger.error(f"❌ No media ID returned for {image_path.name}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to upload {image_path.name} to Facebook: {e}")
            return None
    
    def _check_token_validity(self, platform: str) -> bool:
        """Check if token is valid before posting."""
        try:
            if platform == 'facebook':
                url = f"{self.fb_api_base}/me"
                params = {'access_token': self.fb_access_token}
            else:  # instagram
                url = f"{self.ig_api_base}/{self.ig_user_id}"
                params = {'access_token': self.ig_access_token, 'fields': 'id'}
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                return True
            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"❌ {platform.title()} token validation failed: {error_msg}")
                
                if 'expired' in error_msg.lower() or 'invalid' in error_msg.lower():
                    logger.error(f"🔄 {platform.title()} token has expired!")
                    logger.error("📋 ACTION REQUIRED: Run 'python scripts/token_manager.py' for renewal instructions")
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Error validating {platform} token: {e}")
            return False

    def post_to_facebook(self, image_files: List[Path]) -> bool:
        """Post images to Facebook page."""
        if not image_files:
            logger.warning("No images to post to Facebook")
            return False
        
        # Check token validity first
        if not self._check_token_validity('facebook'):
            logger.error("❌ Facebook token is invalid - skipping Facebook posting")
            return False
        
        logger.info(f"📘 Posting {len(image_files)} images to Facebook...")
        
        try:
            if len(image_files) == 1:
                # Single image post
                image_path = image_files[0]
                url = f"{self.fb_api_base}/{self.fb_page_id}/photos"
                
                with open(image_path, 'rb') as image_file:
                    files = {'source': image_file}
                    data = {
                        'access_token': self.fb_access_token,
                        'published': 'true'
                    }
                    
                    response = requests.post(url, files=files, data=data)
                    response.raise_for_status()
                    
                    result = response.json()
                    post_id = result.get('post_id') or result.get('id')
                    
                    if post_id:
                        logger.info(f"✅ Successfully posted single image to Facebook (Post ID: {post_id})")
                        return True
                    else:
                        logger.error("❌ No post ID returned from Facebook")
                        return False
            
            else:
                # Multiple images - create album/carousel
                logger.info("Creating Facebook album with multiple images...")
                
                # Upload all images first
                media_ids = []
                for image_path in image_files:
                    media_id = self.upload_image_to_facebook(image_path)
                    if media_id:
                        media_ids.append(media_id)
                    else:
                        logger.error(f"Failed to upload {image_path.name}, skipping...")
                
                if not media_ids:
                    logger.error("❌ No images were successfully uploaded")
                    return False
                
                # Create the album post
                url = f"{self.fb_api_base}/{self.fb_page_id}/feed"
                
                # Prepare attached_media for album
                attached_media = [{'media_fbid': media_id} for media_id in media_ids]
                
                data = {
                    'access_token': self.fb_access_token,
                    'attached_media': json.dumps(attached_media)
                }
                
                response = requests.post(url, data=data)
                response.raise_for_status()
                
                result = response.json()
                post_id = result.get('id')
                
                if post_id:
                    logger.info(f"✅ Successfully posted album to Facebook with {len(media_ids)} images (Post ID: {post_id})")
                    return True
                else:
                    logger.error("❌ No post ID returned from Facebook album creation")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to post to Facebook: {e}")
            return False
    
    def upload_image_to_instagram(self, image_path: Path) -> Optional[str]:
        """Upload image to Instagram and return container ID."""
        try:
            # Instagram API requires image_url, not file upload
            # We need to upload to a temporary hosting service or use Facebook's image hosting
            
            # First, upload image to Facebook to get a hosted URL
            fb_upload_url = f"{self.fb_api_base}/{self.fb_page_id}/photos"
            
            with open(image_path, 'rb') as image_file:
                files = {'source': image_file}
                data = {
                    'access_token': self.fb_access_token,
                    'published': 'false'  # Don't publish, just upload for hosting
                }
                
                fb_response = requests.post(fb_upload_url, files=files, data=data)
                fb_response.raise_for_status()
                fb_result = fb_response.json()
                fb_photo_id = fb_result.get('id')
                
                if not fb_photo_id:
                    logger.error(f"❌ Failed to upload {image_path.name} to Facebook for hosting")
                    return None
                
                # Get the hosted image URL from Facebook
                fb_photo_url = f"{self.fb_api_base}/{fb_photo_id}"
                fb_photo_response = requests.get(fb_photo_url, params={'access_token': self.fb_access_token, 'fields': 'images'})
                fb_photo_response.raise_for_status()
                fb_photo_data = fb_photo_response.json()
                
                # Get the largest image URL
                images = fb_photo_data.get('images', [])
                if not images:
                    logger.error(f"❌ No image URLs found for {image_path.name}")
                    return None
                
                image_url = images[0]['source']  # Largest image
                
                # Now create Instagram media container with the hosted URL
                ig_url = f"{self.ig_api_base}/{self.ig_user_id}/media"
                ig_data = {
                    'access_token': self.ig_access_token,
                    'image_url': image_url,
                    'media_type': 'IMAGE'
                }
                
                ig_response = requests.post(ig_url, data=ig_data)
                ig_response.raise_for_status()
                
                ig_result = ig_response.json()
                container_id = ig_result.get('id')
                
                if container_id:
                    logger.info(f"✅ Created Instagram container for {image_path.name} (ID: {container_id})")
                    return container_id
                else:
                    logger.error(f"❌ No container ID returned for {image_path.name}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to upload {image_path.name} to Instagram: {e}")
            # Log more detailed error info
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"   Error details: {error_details}")
                except:
                    logger.error(f"   Response text: {e.response.text}")
            return None
    
    def post_to_instagram(self, image_files: List[Path]) -> bool:
        """Post images to Instagram."""
        if not image_files:
            logger.warning("No images to post to Instagram")
            return False
        
        # Check token validity first
        if not self._check_token_validity('instagram'):
            logger.error("❌ Instagram token is invalid - skipping Instagram posting")
            return False
        
        logger.info(f"📷 Posting {len(image_files)} images to Instagram...")
        
        try:
            if len(image_files) == 1:
                # Single image post
                container_id = self.upload_image_to_instagram(image_files[0])
                if not container_id:
                    return False
                
                # Publish the container
                url = f"{self.ig_api_base}/{self.ig_user_id}/media_publish"
                data = {
                    'access_token': self.ig_access_token,
                    'creation_id': container_id
                }
                
                response = requests.post(url, data=data)
                response.raise_for_status()
                
                result = response.json()
                media_id = result.get('id')
                
                if media_id:
                    logger.info(f"✅ Successfully posted single image to Instagram (Media ID: {media_id})")
                    return True
                else:
                    logger.error("❌ No media ID returned from Instagram")
                    return False
            
            else:
                # Multiple images - create carousel
                logger.info("Creating Instagram carousel with multiple images...")
                
                # Upload all images and get container IDs
                container_ids = []
                for image_path in image_files:
                    container_id = self.upload_image_to_instagram(image_path)
                    if container_id:
                        container_ids.append(container_id)
                    else:
                        logger.error(f"Failed to upload {image_path.name}, skipping...")
                
                if not container_ids:
                    logger.error("❌ No images were successfully uploaded to Instagram")
                    return False
                
                # Instagram has limitations with carousels - let's post the first image only for now
                if container_ids:
                    logger.info(f"📷 Instagram: Posting first image only (Instagram carousel limitations)")
                    
                    # Publish the first container
                    url = f"{self.ig_api_base}/{self.ig_user_id}/media_publish"
                    data = {
                        'access_token': self.ig_access_token,
                        'creation_id': container_ids[0]
                    }
                    
                    response = requests.post(url, data=data)
                    response.raise_for_status()
                    
                    result = response.json()
                    media_id = result.get('id')
                    
                    if media_id:
                        logger.info(f"✅ Successfully posted single image to Instagram (Media ID: {media_id})")
                        logger.info(f"📝 Note: Posted 1 of {len(container_ids)} images due to Instagram API limitations")
                        return True
                    else:
                        logger.error("❌ No media ID returned from Instagram")
                        return False
                else:
                    logger.error("❌ No valid containers for Instagram posting")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to post to Instagram: {e}")
            return False
    
    def post_to_all_platforms(self, output_dir: str = 'output') -> Dict[str, bool]:
        """Post to all social media platforms."""
        logger.info("🚀 Starting social media posting...")
        
        # Get image files
        image_files = self.get_image_files(output_dir)
        if not image_files:
            logger.error("No images found to post")
            return {'facebook': False, 'instagram': False}
        
        results = {}
        
        # Post to Facebook
        logger.info("=" * 50)
        results['facebook'] = self.post_to_facebook(image_files)
        
        # Wait a bit between platforms
        time.sleep(2)
        
        # Post to Instagram
        logger.info("=" * 50)
        results['instagram'] = self.post_to_instagram(image_files)
        
        return results


def main():
    """Main function."""
    logger.info("🎯 Nepali News Social Media Auto-Poster")
    logger.info("=" * 60)
    
    try:
        # Initialize poster
        poster = SocialMediaPoster()
        
        # Post to all platforms
        results = poster.post_to_all_platforms()
        
        # Summary
        logger.info("=" * 60)
        logger.info("📊 POSTING SUMMARY")
        logger.info("=" * 60)
        
        success_count = sum(results.values())
        total_platforms = len(results)
        
        for platform, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"  {platform.upper()}: {status}")
        
        logger.info(f"\nOverall: {success_count}/{total_platforms} platforms successful")
        
        if success_count == total_platforms:
            logger.info("🎉 All posts successful!")
            sys.exit(0)
        elif success_count > 0:
            logger.warning("⚠️ Some posts failed")
            sys.exit(1)
        else:
            logger.error("💥 All posts failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ Posting interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
