#!/usr/bin/env python3
"""
Facebook Token Manager
=====================

Handles Facebook access token validation and provides guidance for renewal.
This script checks token validity and provides instructions for getting long-lived tokens.
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FacebookTokenManager:
    """Manages Facebook access token validation and renewal guidance."""
    
    def __init__(self):
        self.fb_access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.fb_page_id = os.getenv('FACEBOOK_PAGE_ID')
        self.fb_api_base = "https://graph.facebook.com/v18.0"
    
    def check_token_validity(self) -> dict:
        """Check if the current Facebook token is valid and get its info."""
        if not self.fb_access_token:
            return {
                'valid': False,
                'error': 'No Facebook access token found',
                'action_needed': 'Set FACEBOOK_ACCESS_TOKEN environment variable'
            }
        
        try:
            # Check token info
            url = f"{self.fb_api_base}/me"
            params = {
                'access_token': self.fb_access_token,
                'fields': 'id,name'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                # Token is valid, now check if it's a page token
                return self._check_page_token_info()
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                
                return {
                    'valid': False,
                    'error': error_message,
                    'action_needed': 'Token is invalid or expired - needs renewal'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'action_needed': 'Check network connection and token format'
            }
    
    def _check_page_token_info(self) -> dict:
        """Get detailed information about the page token."""
        try:
            # Get token debug info
            url = f"{self.fb_api_base}/debug_token"
            params = {
                'input_token': self.fb_access_token,
                'access_token': self.fb_access_token
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                token_info = response.json().get('data', {})
                
                expires_at = token_info.get('expires_at')
                is_valid = token_info.get('is_valid', False)
                token_type = token_info.get('type', 'unknown')
                
                result = {
                    'valid': is_valid,
                    'type': token_type,
                    'expires_at': expires_at,
                    'app_id': token_info.get('app_id'),
                    'scopes': token_info.get('scopes', [])
                }
                
                if expires_at == 0:
                    result['expiry_status'] = 'Never expires (Long-lived page token)'
                    result['action_needed'] = 'None - Token is properly configured!'
                elif expires_at:
                    expiry_date = datetime.fromtimestamp(expires_at)
                    days_left = (expiry_date - datetime.now()).days
                    
                    result['expiry_date'] = expiry_date.strftime('%Y-%m-%d %H:%M:%S')
                    result['days_left'] = days_left
                    
                    if days_left < 7:
                        result['expiry_status'] = f'Expires in {days_left} days - URGENT RENEWAL NEEDED'
                        result['action_needed'] = 'Generate new long-lived token immediately'
                    elif days_left < 30:
                        result['expiry_status'] = f'Expires in {days_left} days - Plan renewal soon'
                        result['action_needed'] = 'Schedule token renewal'
                    else:
                        result['expiry_status'] = f'Expires in {days_left} days'
                        result['action_needed'] = 'Monitor expiration date'
                else:
                    result['expiry_status'] = 'Unknown expiration'
                    result['action_needed'] = 'Check token configuration'
                
                return result
            else:
                return {
                    'valid': False,
                    'error': 'Could not get token debug info',
                    'action_needed': 'Check token permissions'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'Error checking token info: {str(e)}',
                'action_needed': 'Verify token and network connection'
            }
    
    def get_long_lived_token_instructions(self) -> str:
        """Get instructions for generating a long-lived page token."""
        return """
🔄 HOW TO GET A LONG-LIVED FACEBOOK PAGE TOKEN (Never Expires)

Step 1: Get a Long-Lived User Access Token
==========================================
1. Go to Graph API Explorer: https://developers.facebook.com/tools/explorer/
2. Select your Facebook App
3. Get a User Access Token with these permissions:
   - pages_manage_posts
   - pages_read_engagement
   - pages_show_list
4. Copy this SHORT-LIVED user token

Step 2: Exchange for Long-Lived User Token (60 days)
===================================================
Use this URL (replace YOUR_APP_ID, YOUR_APP_SECRET, SHORT_LIVED_TOKEN):

https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN

Step 3: Get Page Access Token (Never Expires!)
==============================================
Use this URL with the LONG-LIVED user token from Step 2:

https://graph.facebook.com/me/accounts?access_token=LONG_LIVED_USER_TOKEN

Look for your page in the response and copy its "access_token" - this is your NEVER-EXPIRING page token!

Step 4: Update GitHub Secrets
=============================
Update your GitHub repository secrets with the new page token:
- FACEBOOK_ACCESS_TOKEN = the never-expiring page token from Step 3

✅ IMPORTANT: Page tokens don't expire as long as:
- Your app remains active
- You don't change your Facebook password
- You don't revoke app permissions
- Your page remains connected to the app

🔍 You can verify your token using this script:
python scripts/token_manager.py
"""
    
    def check_instagram_token(self) -> dict:
        """Check Instagram token validity."""
        ig_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        ig_user_id = os.getenv('INSTAGRAM_USER_ID')
        
        if not ig_token or not ig_user_id:
            return {
                'valid': False,
                'error': 'Instagram credentials not found',
                'action_needed': 'Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID'
            }
        
        try:
            url = f"{self.fb_api_base}/{ig_user_id}"
            params = {
                'access_token': ig_token,
                'fields': 'id,username'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'valid': True,
                    'username': data.get('username', 'Unknown'),
                    'user_id': data.get('id'),
                    'action_needed': 'None - Instagram token is valid'
                }
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                
                return {
                    'valid': False,
                    'error': error_message,
                    'action_needed': 'Instagram token is invalid - use same page token as Facebook'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'action_needed': 'Check Instagram token configuration'
            }


def main():
    """Main function to check all tokens."""
    logger.info("🔍 Facebook & Instagram Token Validator")
    logger.info("=" * 60)
    
    manager = FacebookTokenManager()
    
    # Check Facebook token
    logger.info("📘 Checking Facebook Token...")
    fb_result = manager.check_token_validity()
    
    print("\n" + "="*60)
    print("📘 FACEBOOK TOKEN STATUS")
    print("="*60)
    
    if fb_result['valid']:
        print("✅ Status: VALID")
        if 'type' in fb_result:
            print(f"📋 Type: {fb_result['type']}")
        if 'expiry_status' in fb_result:
            print(f"⏰ Expiry: {fb_result['expiry_status']}")
        if 'days_left' in fb_result:
            print(f"📅 Days Left: {fb_result['days_left']}")
    else:
        print("❌ Status: INVALID")
        print(f"🚨 Error: {fb_result['error']}")
    
    print(f"🔧 Action Needed: {fb_result['action_needed']}")
    
    # Check Instagram token
    logger.info("\n📷 Checking Instagram Token...")
    ig_result = manager.check_instagram_token()
    
    print("\n" + "="*60)
    print("📷 INSTAGRAM TOKEN STATUS")
    print("="*60)
    
    if ig_result['valid']:
        print("✅ Status: VALID")
        if 'username' in ig_result:
            print(f"👤 Username: @{ig_result['username']}")
    else:
        print("❌ Status: INVALID")
        print(f"🚨 Error: {ig_result['error']}")
    
    print(f"🔧 Action Needed: {ig_result['action_needed']}")
    
    # Show renewal instructions if needed
    if not fb_result['valid'] or (fb_result.get('days_left', 999) < 30):
        print("\n" + "="*60)
        print("🔄 TOKEN RENEWAL INSTRUCTIONS")
        print("="*60)
        print(manager.get_long_lived_token_instructions())
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    fb_status = "✅ OK" if fb_result['valid'] else "❌ NEEDS ATTENTION"
    ig_status = "✅ OK" if ig_result['valid'] else "❌ NEEDS ATTENTION"
    
    print(f"Facebook: {fb_status}")
    print(f"Instagram: {ig_status}")
    
    if fb_result['valid'] and ig_result['valid']:
        print("\n🎉 All tokens are valid! Your automation will work perfectly.")
        return 0
    else:
        print("\n⚠️ Some tokens need attention. Please follow the instructions above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
