# 🌟 Bright Side Daily — Facebook Automation System

> A fully automated, AI-powered Facebook page that posts uplifting content 7 times per day — entirely from GitHub, no server required.

---

## 📁 Folder Structure

```
bright-side-daily/
├── .github/
│   └── workflows/
│       ├── post_scheduler.yml     # Main: posts 7x/day automatically
│       └── weekly_report.yml      # Weekly engagement analytics
│
├── src/
│   ├── scheduler.py               # 🧠 Main orchestrator
│   ├── agents/
│   │   ├── content_agent.py       # 🎯 Picks content, prevents dupes, adapts
│   │   ├── facebook_publisher.py  # 📢 Posts to Facebook via Graph API
│   │   └── performance_agent.py   # 📊 Tracks likes/shares/comments
│   └── generators/
│       └── image_generator.py     # 🖼️  Creates quote poster images
│
├── scripts/
│   └── generate_content_library.py  # 📚 Generates all 2,400 content items
│
├── content/
│   ├── library.json               # Master content index
│   ├── quotes/
│   │   ├── motivational.json      # 500 motivational quotes
│   │   ├── positive_life.json     # 500 positive life quotes
│   │   ├── self_improvement.json  # 300 self-improvement quotes
│   │   ├── gratitude.json         # 300 gratitude quotes
│   │   └── encouragement.json     # 300 encouragement quotes
│   ├── memes/
│   │   └── captions.json          # 300 clean, funny meme captions
│   └── questions/
│       └── engagement.json        # 200 engagement questions
│
├── data/
│   ├── state/
│   │   ├── posted_content.json    # Tracks what's been posted (no dupes)
│   │   ├── successfully_posted.json
│   │   └── failed_posts.json      # Failed posts queued for retry
│   ├── metrics/
│   │   └── engagement.json        # Performance data & adaptive weights
│   └── logs/
│       ├── scheduler.log
│       └── publisher.log
│
├── images/
│   └── output/                    # Generated post images (PNG)
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚡ Quick Start (5 Minutes)

### Step 1 — Fork this repository
Click **Fork** on GitHub. Your automated page lives here.

### Step 2 — Create a Facebook Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com/)
2. **Create App** → Choose **Business** type
3. Add the **Pages** product
4. Go to **Tools → Graph API Explorer**
5. Select your **Facebook Page** (not personal profile)
6. Request permissions: `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`
7. Generate a **Page Access Token** (long-lived, never-expiring via System User)

> 📌 **Important:** Use a System User token for never-expiring access.  
> Guide: [Facebook Long-Lived Tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived)

### Step 3 — Add GitHub Secrets

In your forked repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `FB_PAGE_ID` | Your Facebook Page's numeric ID (found in About section) |
| `FB_PAGE_ACCESS_TOKEN` | The Page Access Token from Step 2 |

### Step 4 — Generate the content library

Run this once to populate all 2,400 content items:

**Option A: Via GitHub Actions** (no local setup needed)
- Go to **Actions → 🌟 Bright Side Daily** → **Run workflow** → set `slot` to `morning_motivation`

**Option B: Locally**
```bash
git clone https://github.com/YOUR_USERNAME/bright-side-daily
cd bright-side-daily
pip install -r requirements.txt
python scripts/generate_content_library.py
git add content/ && git commit -m "Generate content library" && git push
```

### Step 5 — Enable GitHub Actions

- Go to **Actions** tab → Click **"I understand my workflows, go ahead and enable them"**
- The system will now post automatically at all 7 scheduled times.

---

## 📅 Daily Post Schedule (East Africa Time)

| Time (EAT) | Slot | Content Type |
|---|---|---|
| 8:00 AM | Morning Motivation | Motivational quote |
| 10:00 AM | Positive Quote | Positive life quote |
| 12:00 PM | Funny Meme | Clean humor meme |
| 2:00 PM | Self Improvement | Growth/learning quote |
| 4:00 PM | Midday Encouragement | Encouragement quote |
| 7:00 PM | Evening Reflection | Gratitude quote |
| 9:00 PM | Engagement Question | Question for followers |

---

## 🤖 How the AI Agents Work

### 🎯 Content Selection Agent
- Picks unique content from 2,400 items
- Tracks every post to prevent repeats
- When a category runs low (< 30 items), it resets and cycles
- Adapts selection based on engagement performance data

### 🖼️ Image Generator
- Creates 1080×1080 px Facebook-optimized images
- 8 color palette themes (sunrise gold, ocean calm, forest green, etc.)
- Smart visual selection based on quote topic keywords
- Adds branding, decorative borders, typography overlays
- 3 visual styles: photography-style gradients, illustration, minimalist

### 📢 Facebook Publisher
- Posts photo + caption via Facebook Graph API
- Built-in retry logic (3 attempts with 30s delays)
- Falls back to text-only if image generation fails
- Logs all successes and failures separately

### 📊 Performance Agent
- Collects likes, comments, shares, reach per post
- Calculates engagement score per category
- Auto-adjusts content weights (top performers get up to 2× frequency)
- Runs weekly and saves reports to `data/metrics/`

---

## 🧪 Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Generate content library (one-time)
python scripts/generate_content_library.py

# Test a single post (dry run — no Facebook posting)
python src/scheduler.py --slot morning_motivation --dry-run

# Test all 7 posts (dry run)
python src/scheduler.py --all --dry-run

# View the schedule
python src/scheduler.py --schedule

# Run performance report
python src/agents/performance_agent.py report

# Retry failed posts
python src/scheduler.py --retry-failed
```

---

## 🎨 Image Visual Themes

| Category | Color Themes | Typical Backgrounds |
|---|---|---|
| Morning Motivation | Sunrise Gold, Midnight Blue | Mountain summit, open road |
| Positive Quote | Warm Rose, Forest Green | Friends laughing, flowers |
| Funny Meme | Warm Cream, Lavender | Cat with coffee, office chaos |
| Self Improvement | Ocean Calm, Midnight Blue | Books, journal, workspace |
| Encouragement | Sunrise Gold, Warm Rose | Light through forest, lighthouse |
| Gratitude | Warm Cream, Sunrise Gold | Coffee window, flowers |
| Engagement | Ocean Calm, Forest Green | Speech bubbles, community |

---

## 📊 Content Library Summary

| Category | Count |
|---|---|
| Motivational Quotes | 500 |
| Positive Life Quotes | 500 |
| Self-Improvement Quotes | 300 |
| Gratitude Quotes | 300 |
| Encouragement Quotes | 300 |
| Meme Captions | 300 |
| Engagement Questions | 200 |
| **Total** | **2,400** |

---

## ♻️ Content Lifecycle

1. Content is selected and marked as posted
2. Each category tracks its own "used" list
3. When fewer than 30 items remain, the used list resets (cycles)
4. High-performing categories are selected more often (adaptive weights)
5. You can always add more content to JSON files manually

---

## 🔧 Customization

### Change posting times
Edit `.github/workflows/post_scheduler.yml` — modify the `cron` lines (UTC time).

### Add your own quotes
Add items to any JSON file under `content/`. The format is:
```json
{
  "items": ["Your quote here", "Another quote here"],
  "total": 2
}
```

### Change brand name
Search and replace `Bright Side Daily` in `src/generators/image_generator.py`.

### Change color themes
Edit `THEMES` dict in `src/generators/image_generator.py`.

---

## 🚨 Troubleshooting

| Issue | Fix |
|---|---|
| "Missing FB_PAGE_ACCESS_TOKEN" | Add secret to GitHub → Settings → Secrets |
| Posts stop working after 60 days | Refresh your Page Access Token |
| Images not generating | Check `data/logs/scheduler.log` for Pillow errors |
| Duplicate posts | Delete `data/state/posted_content.json` to reset |
| Workflow not running | Enable Actions in repo settings |

---

## 📄 License

MIT — Free to use and modify for your own pages.

---

*Built with ❤️ by Bright Side Daily Bot | Powered by Python + GitHub Actions*
