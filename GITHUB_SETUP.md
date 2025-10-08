# GitHub Actions Setup Guide

This guide will help you set up automated news post generation on GitHub Actions.

## 🔧 Prerequisites

1. A GitHub account
2. This repository pushed to GitHub
3. OpenRouter API key (for DeepSeek LLM)

## 📋 Step-by-Step Setup

### 1. Push Repository to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Automated Nepali news summarizer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 2. Add GitHub Secrets

Go to your repository on GitHub:
1. Click **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secret:

**Secret Name:** `DEEPSEEK_API_KEY`  
**Secret Value:** Your OpenRouter API key (e.g., `sk-or-v1-...`)

### 3. Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. If prompted, click **I understand my workflows, go ahead and enable them**
3. The workflow will now run automatically at scheduled times

### 4. Verify Setup

#### Test Manual Run:
1. Go to **Actions** tab
2. Click on **Automated Nepali News Posts** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait for completion and check the results

## ⏰ Automated Schedule

The workflow runs automatically 3 times per day (Nepal Time):

| Time (NPT) | Time Range | Description |
|------------|------------|-------------|
| 10:30 AM | 5:30 AM - 10:30 AM | Morning news |
| 3:30 PM | 11:00 AM - 3:30 PM | Afternoon news |
| 8:30 PM | 3:30 PM - 8:30 PM | Evening news |

## 📁 Output Files

After each run, the workflow generates:

- **Posts**: `output/combined_news_post_*.png` (multiple posts if needed)
- **Summaries**: `multi_source_summaries.json`
- **Articles**: `multi_source_articles.json`
- **Links**: `multi_source_links.json`

### Accessing Generated Files:

1. Go to **Actions** tab
2. Click on a completed workflow run
3. Scroll down to **Artifacts**
4. Download the artifact (e.g., `news-posts-morning-2025-01-06_10-30`)

## 🗂️ Archive Structure

Generated posts are automatically archived in the repository:

```
archives/
├── morning/
│   └── 2025-01-06_10-30/
│       ├── combined_news_post_1.png
│       ├── combined_news_post_2.png
│       └── multi_source_summaries.json
├── afternoon/
│   └── 2025-01-06_15-30/
│       └── ...
└── evening/
    └── 2025-01-06_20-30/
        └── ...
```

## 🎛️ Configuration

### Adjust Number of Summaries Per Post

Edit `.github/workflows/automated_news_posts.yml`:

```yaml
- name: Generate social media posts
  run: |
    python -m src.generate_posts_playwright --force --max-per-post 8
```

Default is 6 summaries per post.

### Change Schedule Times

Edit the `cron` expressions in `.github/workflows/automated_news_posts.yml`:

```yaml
schedule:
  # Format: minute hour day month day-of-week (UTC time)
  - cron: '45 4 * * *'   # 10:30 AM NPT (UTC+5:45)
  - cron: '45 9 * * *'   # 3:30 PM NPT
  - cron: '45 14 * * *'  # 8:30 PM NPT
```

**Note**: GitHub Actions uses UTC time. Nepal is UTC+5:45.

## 🐛 Troubleshooting

### Workflow Fails

1. Check **Actions** tab for error logs
2. Verify `DEEPSEEK_API_KEY` secret is set correctly
3. Ensure API key has sufficient credits

### No Posts Generated

1. Check if articles were scraped successfully
2. Verify `background.png` exists in repository root
3. Check workflow logs for specific errors

### Posts Look Wrong

1. Ensure `background.png` is 1080x1920 or similar aspect ratio
2. Check if Nepali fonts are loading (Google Fonts CDN)
3. Verify summaries in `multi_source_summaries.json` are correct

## 📊 Monitoring

### View Workflow Status

Go to **Actions** tab to see:
- ✅ Successful runs (green checkmark)
- ❌ Failed runs (red X)
- 🟡 In-progress runs (yellow dot)

### Check Summary

Each workflow run creates a summary showing:
- Time slot (morning/afternoon/evening)
- Number of articles processed
- Number of posts generated
- Status

## 🔄 Manual Trigger

To run the workflow manually:

1. Go to **Actions** → **Automated Nepali News Posts**
2. Click **Run workflow**
3. Select time slot (optional)
4. Click **Run workflow**

## 📝 Notes

- The workflow requires ~5-10 minutes to complete
- Generated posts are kept for 30 days as artifacts
- Archived posts are committed to the repository permanently
- Free GitHub Actions includes 2,000 minutes/month for public repos

## 🎉 Success!

Once set up, your Nepali news posts will be generated automatically 3 times daily with perfect Devanagari text rendering!
