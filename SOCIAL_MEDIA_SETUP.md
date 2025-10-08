# Social Media Auto-Posting Setup Guide

This guide will help you set up automated posting to Facebook and Instagram for your Nepali news project.

## Overview

The system now automatically:
1. **Scrapes** news from multiple Nepali sources
2. **Summarizes** using AI (DeepSeek)
3. **Generates** beautiful social media posts
4. **Posts automatically** to Facebook & Instagram
5. **Uploads** to Google Drive for backup

## Required API Credentials

You need to set up these environment variables in your GitHub repository secrets:

### Facebook API Setup (IMPORTANT: Get Never-Expiring Token!)

1. **Create Facebook App**:
   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create a new app
   - Add "Pages" product to your app

2. **Get Long-Lived Page Access Token (Never Expires!)**:
   
   **Step 2a**: Get Short-Lived User Token
   - Go to Graph API Explorer
   - Select your app
   - Get User Access Token with permissions: `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`
   
   **Step 2b**: Exchange for Long-Lived User Token (60 days)
   ```
   https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN
   ```
   
   **Step 2c**: Get Never-Expiring Page Token
   ```
   https://graph.facebook.com/me/accounts?access_token=LONG_LIVED_USER_TOKEN
   ```
   Use the `access_token` from your page in the response - this NEVER expires!

3. **Required GitHub Secrets**:
   ```
   FACEBOOK_ACCESS_TOKEN=your_never_expiring_page_token_here
   FACEBOOK_PAGE_ID=your_facebook_page_id_here
   ```

### Instagram API Setup

1. **Convert to Business Account**:
   - Your Instagram account must be a Business account
   - Connect it to your Facebook page

2. **Get Instagram Business Account ID**:
   - Use Graph API Explorer: `/{page-id}?fields=instagram_business_account`
   - Note down the Instagram Business Account ID

3. **Required GitHub Secrets**:
   ```
   INSTAGRAM_ACCESS_TOKEN=your_never_expiring_page_token_here
   INSTAGRAM_USER_ID=your_instagram_business_account_id_here
   ```
   
   **Note**: Use the SAME never-expiring page token for Instagram!

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each of these secrets:

```
FACEBOOK_ACCESS_TOKEN
FACEBOOK_PAGE_ID
INSTAGRAM_ACCESS_TOKEN
INSTAGRAM_USER_ID
```

## How It Works

### Posting Logic
- **Single Image**: Posts directly to both platforms
- **Multiple Images**: Creates albums/carousels on both platforms
- **No Captions**: Posts images only (as requested)
- **Error Handling**: Continues if one platform fails

### Posting Schedule
The system runs 3 times daily (Nepal Time):
- **10:30 AM**: Morning news (5:30 AM - 10:30 AM)
- **3:30 PM**: Afternoon news (11:00 AM - 3:30 PM)
- **8:30 PM**: Evening news (3:30 PM - 8:30 PM)

### Workflow Order
1. Scrape news articles
2. Extract and clean content
3. Generate AI summaries
4. Create social media post images
5. **🆕 Post to Facebook & Instagram**
6. Upload images to Google Drive
7. Archive results in GitHub

## Token Management & Monitoring

### Automatic Token Validation
The system now includes automatic token validation:

```bash
# Check token status and get renewal instructions
python scripts/token_manager.py
```

This script will:
- ✅ **Check if tokens are valid**
- ⏰ **Show expiration dates**
- 🔄 **Provide renewal instructions**
- 📋 **Guide you through getting never-expiring tokens**

### GitHub Actions Integration
- **Token validation** runs before every posting attempt
- **Detailed error messages** if tokens are expired
- **Continues automation** even if social media posting fails

## Testing

### Manual Testing
You can test the posting manually:

```bash
# Set environment variables
export FACEBOOK_ACCESS_TOKEN="your_token"
export FACEBOOK_PAGE_ID="your_page_id"
export INSTAGRAM_ACCESS_TOKEN="your_token"
export INSTAGRAM_USER_ID="your_user_id"

# Check token status first
python scripts/token_manager.py

# Run the poster (make sure you have images in output/ folder)
python scripts/post_to_social.py
```

### GitHub Actions Testing
- Go to **Actions** tab in your repository
- Click **Automated Nepali News Posts**
- Click **Run workflow** to test manually

## Troubleshooting

### Common Issues

1. **"Invalid Access Token"**
   - Token might be expired
   - Regenerate token from Facebook Developers
   - Update GitHub secrets

2. **"Insufficient Permissions"**
   - Make sure your token has required permissions:
     - `pages_manage_posts`
     - `pages_read_engagement`
     - `instagram_basic`

3. **"Page Not Found"**
   - Double-check your Facebook Page ID
   - Make sure the page is connected to your app

4. **Instagram Posting Fails**
   - Ensure Instagram account is Business account
   - Verify it's connected to your Facebook page
   - Check Instagram Business Account ID

### Getting Help

1. **Check GitHub Actions logs** for detailed error messages
2. **Test API calls** using Graph API Explorer
3. **Verify permissions** in Facebook App settings

## Security Notes

- **Never commit API tokens** to your repository
- **Use GitHub Secrets** for all sensitive credentials
- **Regularly rotate** your access tokens
- **Monitor usage** in Facebook Developers console

## Features

✅ **Multi-platform posting** (Facebook + Instagram)  
✅ **Multiple image support** (albums/carousels)  
✅ **No captions** (image-only posts)  
✅ **Error handling** and retry logic  
✅ **Detailed logging** for debugging  
✅ **Automated scheduling** via GitHub Actions  

Your Nepali news automation system is now complete with social media posting! 🎉
