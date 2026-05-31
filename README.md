<div align="center">

# 🔍 SEO Audit Tool

### Production-ready SEO analyzer — 80+ checks, real crawling, auto-fix support

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![React](https://img.shields.io/badge/React-18-61dafb)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![License](https://img.shields.io/badge/license-MIT-orange)

</div>

---

## 📌 Overview

SEO Audit Tool is a full-stack application that performs **real-time SEO audits** on any website.
It actually crawls the website, parses the HTML, and runs 80+ checks across 9 categories.

**No paid API key required** — everything is free and runs locally.

---

## ✨ Features

- ✅ **80+ Real SEO Checks** — actual HTTP crawl + BeautifulSoup HTML parsing
- ✅ **9 Categories** — Technical, Meta Tags, Performance, Content, Images, Headings, Links, Security, Social
- ✅ **Live Progress** — real-time audit progress bar with step-by-step updates
- ✅ **Score 0–100** — weighted overall score + per-category scores
- ✅ **Bar Chart + Radar Chart** — visual category breakdown
- ✅ **Quick Wins** — auto-fixable issues highlighted separately
- ✅ **Issue Accordion** — click any issue to see description, recommendation, current/expected values
- ✅ **Severity Filters** — filter by Critical / Warning / Info / Pass
- ✅ **Auto-Fix Support** — automatically apply fixes via WordPress REST API
- ✅ **Export** — download reports as JSON or CSV
- ✅ **Zero API Cost** — no Anthropic, OpenAI, or any paid service required

---

## 🏗️ Project Structure

```
seo-audit-tool/
│
├── frontend/                        # React Application
│   ├── src/
│   │   ├── SEOAuditTool.jsx         # ⭐ Main component (use this one)
│   │   └── index.js                 # React entry point
│   ├── public/
│   │   └── index.html
│   └── package.json
│
├── backend/                         # FastAPI Python Server
│   ├── main.py                      # All endpoints + 80+ SEO check logic
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Environment variables template
│
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| npm | 9+ | Comes with Node.js |

---

### Step 1 — Backend Setup

```bash
# Navigate to the backend folder
cd backend

# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

✅ Backend running at: `http://localhost:8000`
📄 API Docs: `http://localhost:8000/docs`

---

### Step 2 — Frontend Setup

```bash
# Open a new terminal and navigate to the frontend folder
cd frontend

# Install dependencies (first time only)
npm install

# Start the app
npm start
```

✅ Frontend running at: `http://localhost:3000`

---

### Step 3 — Run an Audit

1. Open `http://localhost:3000` in your browser
2. Enter any website URL (e.g. `https://github.com`)
3. Click the **Audit** button
4. View your results 🎉

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/audit` | Start a new audit |
| `GET` | `/api/audit/{id}` | Get audit status / full report |
| `GET` | `/api/progress/{id}` | Get live progress percentage |
| `POST` | `/api/auto-fix/{issue_id}` | Apply an auto-fix (WP credentials required) |
| `GET` | `/api/export/{id}?format=json` | Download JSON report |
| `GET` | `/api/export/{id}?format=csv` | Download CSV report |
| `WS` | `/ws/audit-progress` | WebSocket real-time progress |
| `GET` | `/docs` | Swagger UI (interactive API docs) |
| `GET` | `/redoc` | ReDoc API documentation |

---

## 📊 SEO Checks — 80+ Total

### 🔧 Technical (20%)
- HTTPS enabled
- robots.txt accessible and valid
- XML Sitemap present
- Schema.org / JSON-LD structured data
- URL structure and length
- Render-blocking JavaScript in `<head>`
- Query parameters in URL

### 🏷️ Meta Tags (18%)
- Title tag — presence, length (50–60 chars)
- Meta description — presence, length (150–160 chars)
- Viewport meta tag
- Canonical tag
- HTML `lang` attribute
- Charset declaration
- Meta robots (noindex/nofollow detection)

### ⚡ Performance (17%)
- Time to First Byte (TTFB)
- Gzip/Brotli compression
- Cache-Control headers
- HTML page size
- CSS file count
- JavaScript file count
- Render-blocking resources

### 📝 Content (14%)
- Word count (300+ recommended)
- Paragraph structure
- Content/HTML ratio

### 🖼️ Images (10%)
- Missing alt text
- `loading="lazy"` attribute
- Width/Height dimensions
- Total image count

### 📰 Headings (8%)
- H1 presence and count
- H1 quality (length)
- Heading hierarchy (H1→H2→H3)
- Empty heading tags

### 🔗 Links (7%)
- Internal links count
- Generic anchor text ("click here", "read more")
- External links without nofollow
- Total link count (100 limit)

### 🔒 Security (4%)
- HTTPS certificate
- X-Frame-Options header
- HSTS (Strict-Transport-Security)
- X-Content-Type-Options
- Content-Security-Policy
- X-XSS-Protection

### 📱 Social (2%)
- Open Graph title (og:title)
- Open Graph description (og:description)
- Open Graph image (og:image)
- Twitter Card meta tag

---

## 🔧 Auto-Fix Feature (WordPress)

If you have a WordPress site, the **auto-fix** feature can automatically resolve issues.

### Setup

1. Go to your WordPress Admin panel
2. Navigate to **Users → Your Profile → Application Passwords**
3. Click "Add New Application Password" — enter a name (e.g. "SEO Tool") → Generate
4. Copy the generated password

### Enter Credentials in the Audit Tool

Expand the **"Admin access"** section on the input screen:

```
WP REST API URL:   https://yoursite.com/wp-json
Username:          your-wp-username
Password:          xxxx xxxx xxxx xxxx xxxx
```

### Supported Auto-Fixes

| Issue | What it does |
|-------|-------------|
| Missing title tag | Sets post title via WP REST API |
| Missing meta description | Injects via Yoast/RankMath API |
| Missing viewport tag | Adds to functions.php |
| Missing canonical tag | Sets via SEO plugin |
| Images missing lazy loading | Adds `loading="lazy"` via content filter |
| Missing schema markup | Injects JSON-LD block |
| Render-blocking JS | Adds `async` attribute to scripts |
| Missing OG image | Sets featured image as OG image |

---

## 🌐 Custom Backend URL

If your backend runs on a different host or port, create a `.env` file in the frontend folder:

```bash
# frontend/.env
REACT_APP_API_URL=http://192.168.1.100:8000
```

---

## 🛠️ Tech Stack

### Frontend
| Library | Purpose |
|---------|---------|
| React 18 | UI framework |
| Recharts | Bar chart + Radar chart |
| Lucide React | Icons |
| Tailwind CSS | Utility styling |

### Backend
| Library | Purpose |
|---------|---------|
| FastAPI | REST API + WebSocket server |
| httpx | Async HTTP requests (website crawling) |
| BeautifulSoup4 | HTML parsing |
| lxml | Fast HTML parser |
| Pydantic | Data validation |
| uvicorn | ASGI server |

---

## ❓ Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version   # needs 3.10+

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Frontend CORS error
```
Make sure the backend is running on port 8000
uvicorn main:app --reload --port 8000
```

### `npm start` not working
```bash
# Delete node_modules and reinstall
rmdir /s /q node_modules   # Windows
npm install
npm start
```

### Audit shows "Failed"
- Check the backend terminal for error details
- Is the URL correct? (must start with `https://`)
- Is the website publicly accessible?

---

## 📈 Score Calculation

```
Overall Score = Weighted Average of all categories

Technical   × 20%
Meta Tags   × 18%
Performance × 17%
Content     × 14%
Images      × 10%
Headings    ×  8%
Links       ×  7%
Security    ×  4%
Social      ×  2%

Per category score:
  Starting score : 100
  Critical issue : -18 points
  Warning issue  :  -7 points
  Info issue     :  -2 points
  Pass           :   0 points  (minimum score: 0)
```

| Score | Rating |
|-------|--------|
| 80–100 | 🟢 Excellent |
| 65–79 | 🟡 Good |
| 45–64 | 🟠 Needs Work |
| 0–44 | 🔴 Poor |

---

## 📄 License

MIT License — free to use, modify, and share.

---

<div align="center">

**Made with ❤️ — No API keys. No subscriptions. Just results.**

</div>
