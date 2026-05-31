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

SEO Audit Tool ek full-stack application hai jo kisi bhi website ka **real-time SEO audit** karta hai.
Yeh tool website ko actually crawl karta hai, HTML parse karta hai aur 9 categories mein 80+ checks run karta hai.

**Koi paid API key ki zaroorat nahi** — sab kuch free aur local hai.

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
- ✅ **Auto-Fix Support** — WordPress REST API se automatic fixes apply karo
- ✅ **Export** — JSON aur CSV download
- ✅ **Zero API Cost** — koi Anthropic, OpenAI ya koi bhi paid service nahi

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
# Backend folder mein jao
cd backend

# Virtual environment banao (recommended)
python -m venv venv

# Virtual environment activate karo
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Dependencies install karo
pip install -r requirements.txt

# Server start karo
uvicorn main:app --reload --port 8000
```

✅ Backend ready: `http://localhost:8000`
📄 API Docs: `http://localhost:8000/docs`

---

### Step 2 — Frontend Setup

```bash
# Naya terminal kholo, frontend folder mein jao
cd frontend

# Dependencies install karo (sirf pehli baar)
npm install

# App start karo
npm start
```

✅ Frontend ready: `http://localhost:3000`

---

### Step 3 — Use Karo

1. Browser mein `http://localhost:3000` kholo
2. Koi bhi website URL daalo (e.g. `https://github.com`)
3. **Audit** button dabao
4. Results dekho 🎉

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/audit` | Naya audit start karo |
| `GET` | `/api/audit/{id}` | Audit status / full report lo |
| `GET` | `/api/progress/{id}` | Live progress percentage |
| `POST` | `/api/auto-fix/{issue_id}` | Auto-fix apply karo (WP credentials chahiye) |
| `GET` | `/api/export/{id}?format=json` | JSON report download |
| `GET` | `/api/export/{id}?format=csv` | CSV report download |
| `WS` | `/ws/audit-progress` | WebSocket real-time progress |
| `GET` | `/docs` | Swagger UI (interactive API docs) |
| `GET` | `/redoc` | ReDoc API documentation |

---

## 📊 SEO Checks — 80+ Total

### 🔧 Technical (20%)
- HTTPS enabled check
- robots.txt accessible aur valid
- XML Sitemap mojood hai
- Schema.org / JSON-LD structured data
- URL structure aur length
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
- CSS files count
- JavaScript files count
- Render-blocking resources

### 📝 Content (14%)
- Word count (300+ recommended)
- Paragraph structure
- Content/HTML ratio

### 🖼️ Images (10%)
- Alt text missing
- `loading="lazy"` attribute
- Width/Height dimensions
- Image count

### 📰 Headings (8%)
- H1 presence aur count
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

Agar aapke paas WordPress site hai toh **auto-fix** feature se issues automatically fix ho sakte hain.

### Setup

1. WordPress Admin panel mein jao
2. **Users → Your Profile → Application Passwords**
3. "Add New Application Password" — naam daalo (e.g. "SEO Tool") → Generate
4. Generated password copy karo

### Audit Tool Mein Credentials Daalo

Input screen pe **"Admin access"** section expand karo:

```
WP REST API URL:   https://yoursite.com/wp-json
Username:          your-wp-username
Password:          xxxx xxxx xxxx xxxx xxxx
```

### Auto-Fix Hone Wale Issues

| Issue | Fix |
|-------|-----|
| Missing title tag | Post title via WP REST API |
| Missing meta description | Yoast/RankMath API se inject |
| Missing viewport tag | functions.php mein add |
| Missing canonical tag | SEO plugin se set |
| Images lazy loading | Content filter se `loading="lazy"` |
| Missing schema markup | JSON-LD block inject |
| Render-blocking JS | `async` attribute add |
| Missing OG image | Featured image se set |

---

## 🌐 Custom Backend URL

Agar backend alag host/port pe ho toh frontend mein `.env` file banao:

```bash
# frontend/.env
REACT_APP_API_URL=http://192.168.1.100:8000
```

---

## 🛠️ Tech Stack

### Frontend
| Library | Use |
|---------|-----|
| React 18 | UI framework |
| Recharts | Bar chart + Radar chart |
| Lucide React | Icons |
| Tailwind CSS | Utility styling |

### Backend
| Library | Use |
|---------|-----|
| FastAPI | REST API + WebSocket |
| httpx | Async HTTP requests (website crawling) |
| BeautifulSoup4 | HTML parsing |
| lxml | Fast HTML parser |
| Pydantic | Data validation |
| uvicorn | ASGI server |

---

## ❓ Troubleshooting

### Backend start nahi ho raha
```bash
# Python version check karo
python --version   # 3.10+ chahiye

# Dependencies dobara install karo
pip install -r requirements.txt --upgrade
```

### Frontend CORS error aa raha hai
```
Backend zaroor chal raha ho port 8000 pe
uvicorn main:app --reload --port 8000
```

### `npm start` kaam nahi kar raha
```bash
# node_modules delete karo aur dobara install karo
rm -rf node_modules
npm install
npm start
```

### Audit "Failed" dikha raha hai
- Check karo backend terminal mein error message
- URL sahi hai? (`https://` se shuru hona chahiye)
- Website publicly accessible hai?

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

Per category:
  Start: 100
  Critical issue: -18 points
  Warning issue:  -7  points
  Info issue:     -2  points
  Pass:            0  points (minimum: 0)
```

| Score | Rating |
|-------|--------|
| 80–100 | 🟢 Excellent |
| 65–79 | 🟡 Good |
| 45–64 | 🟠 Needs Work |
| 0–44 | 🔴 Poor |

---

## 📄 License

MIT License — free hai, use karo, modify karo, share karo.

---

<div align="center">

**Made with ❤️ — No API keys, No subscriptions, Just results.**

</div>
