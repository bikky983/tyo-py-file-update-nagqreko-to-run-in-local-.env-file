# 🚀 Complete Google Drive Setup Guide

This guide will help you set up automatic Google Drive uploads for your Nepali news post images using your personal Gmail account.

## 📋 What You'll Achieve

After this setup:
- ✅ Generated news post images automatically upload to Google Drive
- ✅ Organized in folders: `NepaliNewsPosts/YYYY-MM-DD/morning|afternoon|evening/`
- ✅ Works with your personal Gmail account (no organization needed)
- ✅ Fully automated via GitHub Actions
- ✅ Only uploads PNG images (no JSON files)

## 🔧 Step 1: Google Cloud Console Setup

### 1.1 Create Project
1. Go to: https://console.cloud.google.com/
2. Sign in with your personal Gmail
3. Click project dropdown → **"New Project"**
4. Name: `Nepali News Bot`
5. Location: "No organization"
6. Click **"Create"**

### 1.2 Enable Google Drive API
1. Select your new project
2. Go to **"APIs & Services"** → **"Library"**
3. Search: `Google Drive API`
4. Click **"Google Drive API"** → **"Enable"**

### 1.3 Configure OAuth Consent Screen
1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"** → **"Create"**
3. Fill required fields:
   - **App name**: `Nepali News Bot`
   - **User support email**: Your Gmail
   - **Developer contact**: Your Gmail
4. Click **"Save and Continue"** through all steps
5. On "Test users" page, add your Gmail address

### 1.4 Create OAuth Credentials
1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Select **"Desktop application"**
4. Name: `Nepali News Rclone`
5. Click **"Create"**
6. **SAVE**: Note the Client ID and Client Secret

## 🖥️ Step 2: Local Rclone Setup

### 2.1 Install Rclone (Windows)
```powershell
# Download Rclone
Invoke-WebRequest -Uri "https://downloads.rclone.org/rclone-current-windows-amd64.zip" -OutFile "rclone.zip"

# Extract to C:\rclone\
Expand-Archive -Path "rclone.zip" -DestinationPath "C:\rclone\"

# Add C:\rclone\ to your Windows PATH
```

### 2.2 Configure Rclone
Open Command Prompt and run:
```bash
rclone config
```

Follow these steps:
1. **Choose**: `n` (New remote)
2. **Name**: `gdrive`
3. **Storage**: `drive` (Google Drive)
4. **Client ID**: Paste your OAuth Client ID
5. **Client Secret**: Paste your OAuth Client Secret
6. **Scope**: `1` (Full access)
7. **Root folder ID**: Press Enter (empty)
8. **Service Account**: Press Enter (empty)
9. **Advanced config**: `n` (No)
10. **Auto config**: `y` (Yes) - Browser will open
11. **Sign in**: Use your Gmail and grant permissions
12. **Team drive**: `n` (No)
13. **Confirm**: `y` (Yes)

### 2.3 Test Configuration
```bash
# Test connection
rclone ls gdrive:

# Create folder for news posts
rclone mkdir gdrive:NepaliNewsPosts

# Test upload
echo "Test" > test.txt
rclone copy test.txt gdrive:NepaliNewsPosts/
```

### 2.4 Get Config for GitHub
```bash
# Show your config (copy the [gdrive] section)
rclone config show
```

Copy the entire `[gdrive]` section output - you'll need this for GitHub Secrets.

## 🔐 Step 3: GitHub Secrets Setup

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add this secret:

**Name**: `RCLONE_CONFIG`
**Value**: Paste the entire `[gdrive]` section from `rclone config show`

Example format:
```
[gdrive]
type = drive
client_id = your_client_id_here
client_secret = your_client_secret_here
scope = drive
token = {"access_token":"...","token_type":"Bearer",...}
team_drive = 
```

## 🚀 Step 4: Deploy and Test

### 4.1 Push Changes
```bash
git add .
git commit -m "Add Google Drive integration"
git push origin main
```

### 4.2 Test Manual Run
1. Go to **Actions** tab in GitHub
2. Click **"Automated Nepali News Posts"**
3. Click **"Run workflow"** → **"Run workflow"**
4. Wait for completion

### 4.3 Check Results
After the workflow completes:
1. Check your Google Drive
2. Look for folder: `NepaliNewsPosts/YYYY-MM-DD/morning/`
3. Verify PNG files are uploaded

## 📁 Folder Structure

Your Google Drive will have this structure:
```
NepaliNewsPosts/
├── 2025-10-07/
│   ├── morning/
│   │   ├── combined_news_post_1.png
│   │   └── combined_news_post_2.png
│   ├── afternoon/
│   │   └── combined_news_post_1.png
│   └── evening/
│       └── combined_news_post_1.png
├── 2025-10-08/
│   └── ...
```

## 🔧 Troubleshooting

### Issue: "Invalid credentials"
**Solution**: Regenerate OAuth credentials and update GitHub secret

### Issue: "Access denied"
**Solution**: Make sure you granted all permissions during OAuth setup

### Issue: "Rclone not found"
**Solution**: Check that rclone is installed in GitHub Actions (automatic)

### Issue: "No images uploaded"
**Solution**: Check if images were generated in the `output/` folder

## 🎉 Success!

Once set up, your workflow will:
1. ✅ Generate news posts 3x daily
2. ✅ Upload images to organized Google Drive folders
3. ✅ Keep GitHub artifacts as backup
4. ✅ Work completely automatically

**Next**: You can share the Google Drive folder or set up Facebook/Instagram integration!

## 📱 Future Enhancements

- **Facebook Pages API**: Auto-post to Facebook page
- **Instagram Basic Display API**: Auto-post to Instagram
- **Telegram Bot**: Send posts to Telegram channel
- **Email Notifications**: Get notified when posts are uploaded
