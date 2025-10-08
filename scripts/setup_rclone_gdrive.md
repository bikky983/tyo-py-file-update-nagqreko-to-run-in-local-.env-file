# Rclone Google Drive Setup Guide

## Step 1: Install Rclone on Your Local Machine

### For Windows:
1. Download Rclone from: https://rclone.org/downloads/
2. Extract the zip file to `C:\rclone\`
3. Add `C:\rclone\` to your Windows PATH environment variable

### Alternative (using PowerShell):
```powershell
# Download and install Rclone
Invoke-WebRequest -Uri "https://downloads.rclone.org/rclone-current-windows-amd64.zip" -OutFile "rclone.zip"
Expand-Archive -Path "rclone.zip" -DestinationPath "C:\rclone\"
# Add to PATH manually through System Properties
```

## Step 2: Configure Rclone for Google Drive

Open Command Prompt or PowerShell and run:

```bash
rclone config
```

Follow these steps:

1. **Choose option**: `n` (New remote)
2. **Name**: `gdrive` (or any name you prefer)
3. **Storage type**: Type `drive` or find Google Drive in the list
4. **Client ID**: Paste your OAuth Client ID from Google Cloud Console
5. **Client Secret**: Paste your OAuth Client Secret
6. **Scope**: Choose `1` (Full access to all files)
7. **Root folder ID**: Press Enter (leave empty for root)
8. **Service Account File**: Press Enter (leave empty)
9. **Edit advanced config**: `n` (No)
10. **Use auto config**: `y` (Yes) - This will open your browser
11. **Sign in**: Use your personal Gmail account and grant permissions
12. **Configure as team drive**: `n` (No)
13. **Confirm**: `y` (Yes, this is OK)

## Step 3: Test the Configuration

```bash
# List your Google Drive contents
rclone ls gdrive:

# Create a test folder
rclone mkdir gdrive:NepaliNewsPosts

# Test upload
echo "Test file" > test.txt
rclone copy test.txt gdrive:NepaliNewsPosts/
```

## Step 4: Get Rclone Config for GitHub Actions

```bash
# Show your rclone config (you'll need this for GitHub Secrets)
rclone config show
```

Copy the entire `[gdrive]` section - you'll add





 this to GitHub Secrets.

## Important Notes

- The config contains your refresh token, so keep it secure
- Never commit the rclone config to your repository
- The token will work for GitHub Actions automation
