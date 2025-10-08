# 🚀 Quick Start Guide

## Local Testing (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Add API key to .env
# Edit .env file and add: DEEPSEEK_API_KEY=sk-or-v1-...

# 3. Run pipeline
python main.py

# 4. Generate posts
python -m src.generate_posts_playwright --force

# Done! Check output/ folder for posts
```

## GitHub Actions Setup (5 minutes)

```bash
# 1. Push to GitHub
git add .
git commit -m "Automated Nepali news system"
git push origin main

# 2. Add API key secret
# GitHub → Settings → Secrets → Actions
# Add: DEEPSEEK_API_KEY = sk-or-v1-...

# 3. Enable workflows
# GitHub → Actions → Enable

# Done! Posts auto-generate 3x daily
```

## Schedule

- **10:30 AM NPT** - Morning news
- **3:30 PM NPT** - Afternoon news  
- **8:30 PM NPT** - Evening news

## Key Files

- `main.py` - Run scraping & summarization
- `src/generate_posts_playwright.py` - Generate posts
- `.github/workflows/automated_news_posts.yml` - Automation
- `GITHUB_SETUP.md` - Detailed setup guide
- `FINAL_SUMMARY.md` - Complete documentation

## Features

✅ Perfect Nepali text (क्ष, ग्र, स्त, र्ग)  
✅ Multi-post generation  
✅ No article limits  
✅ Fully automated  
✅ 3x daily runs

**That's it! Your automated Nepali news system is ready!** 🎉
