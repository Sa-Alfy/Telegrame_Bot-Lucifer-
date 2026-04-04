# Lucifer — AI-Powered Telegram Bot

A highly advanced, modular, and multi-featured Telegram bot built with Python. Lucifer combines AI chat, image generation, daily utilities, interactive games, and media tools — all in one seamlessly integrated bot. Fully bilingual (Bengali & English).

---

## 🚀 Features

### 🧠 Artificial Intelligence
| Feature | Command | Description |
|:---|:---|:---|
| **AI Chat (Multimodal)** | `(Just Type)` | Talk to Llama 3 via Groq. Supports text and photo analysis. |
| **AI Personas** | `/persona` | Switch the AI's personality (Gen-Z, Professional, Sarcastic, Pirate). |
| **AI Image Generator** | `/image` | Generate stunning high-res AI art using Stable Diffusion XL (Flux.1). |
| **OCR Text Extraction** | `/ocr` | Reply to any image to instantly extract all text from it. |

### 🛠️ Daily Utilities
| Feature | Command | Description |
|:---|:---|:---|
| **Daily News Digest** | `/news [bd]` | Fetches live top headlines from BBC World and The Daily Star (RSS). |
| **Live Weather** | `/weather <city>` | Check real-time weather, temperature, and forecasts worldwide. |
| **Daraz Deal Finder** | `/find <product>` | Scrapes and finds the best current product deals on Daraz.com.bd. |
| **Media Downloader** | `/download <url>` | Instantly download videos/audio from YouTube, TikTok, Facebook, etc. |
| **Translation** | `/translate <text>` | Auto-detects and translates any language into English and Bengali. |
| **Currency Converter** | `/convert` | Real-time live exchange rates between all major global currencies. |
| **QR Code Generator** | `/qr <text>` | Generates an instant, scannable QR code from any link or text. |
| **Telegram Sticker Maker**| `/sticker` | Convert any photo, or generate new AI images, into Telegram Stickers. |

### 🎮 Entertainment & Social
| Feature | Command | Description |
|:---|:---|:---|
| **Interactive Minigames** | `/play` | Play AI-driven games like Word Chain, Antakshari, and Bargaining! |
| **Trivia Quizzes** | `/quiz <topic>` | Generates a 3-question interactive quiz on any topic you want. |
| **Voice Text-To-Speech** | `/say`, `/say_as_girl` | Converts text into high-quality spoken audio (Male or Female). |
| **User Profiles** | `/me` | Tracks your usage, points, rank, quiz accuracy, and active persona. |
| **Memory Manager** | `/clear` | Safely erases chat context memory to start a fresh conversation. |

### ⚙️ Admin & Backend
- **Global Error Handling:** Smartly truncates text and bypasses API crashes to ensure the bot never hangs.
- **Admin Debug Panel** (`/debug`): Monitor API health, uptime, and toggle specific module services on/off.
- **Persistent State Management:** Automatically saves user ranks, chat quotas, and memory using background threads.
- **Robust Logging:** Implements rotating log files (max 5MB) ensuring stable long-term server deployment.

---

## 📂 Project Structure

```
my_telegram_bot/
├── main.py              # Entry point — starts the bot + health check server
├── config.py            # Loads environment variables securely
├── state.py             # Manages user profiles, DB state, and command tracking
├── Procfile             # Deployment config for Koyeb
├── requirements.txt     # Python dependencies
├── .env.example         # Template for environment variables
│
├── handlers/            # Telegram command & message logic (18+ modules)
│   ├── basic.py         # Start menus, help popups
│   ├── news.py          # Daily news digest
│   ├── sticker.py       # Sticker maker logic
│   ├── games.py         # AI minigames and interactive state
│   └── ...              # (qr, quiz, weather, download, ocr, translate, etc.)
│
├── services/            # Business logic & 3rd Party Integrations
│   ├── ai_chat.py       # Groq API / Llama integration
│   ├── news_service.py  # Zero-dependency async RSS fetcher
│   ├── downloader.py    # yt-dlp media extraction wrapper
│   └── ...              # (currency, image_gen, weather, etc.)
│
└── utils/               # Helpers
    ├── format.py        # Telegram HTML sanitizer & formatting tools
    ├── logger.py        # Centralized async rotating file logger
    ├── constants.py     # Fallback models and global configs
    └── decorators.py    # Rate limiting and cooldown injection
```

---

## 🚀 Quick Start (Local)

### 1. Clone the Repository

```bash
git clone https://github.com/Sa-Alfy/Telegrame_Bot-Lucifer-.git
cd Telegrame_Bot-Lucifer-
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys (Everything is free tier!):

| Key | Where to Get It |
|:---|:---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com/) |
| `IMAGE_GEN_KEY` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `OPENWEATHERMAP_API_KEY` | [openweathermap.org/api](https://openweathermap.org/api) |
| `ADMIN_ID` | Send a message to your bot and check the app logs |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) (optional) |

### 5. Run the Bot

```bash
python main.py
```

---

## ☁️ Deploy to Koyeb (Free, 24/7)

Koyeb provides free hosting with no credit card needed.

### Step 1: Push to GitHub
Make sure your code is on GitHub (your `.env` is safely excluded by `.gitignore`).

### Step 2: Create a Koyeb Account
Sign up at [koyeb.com](https://www.koyeb.com/) — no credit card required.

### Step 3: Create a New Service
1. Click **"Create Service"** → **"GitHub"**
2. Connect your GitHub account and select this repository.
3. Set the Builder to **Buildpack**.
4. Set the Run command to `python main.py`.
5. Set the Port to `8000`.

### Step 4: Add Environment Variables
In the Koyeb service settings, add each key from `.env` as an environment variable. Never paste keys into your code!

### Step 5: Deploy
Click Deploy — Koyeb will build and start your bot automatically. Features like the `.news` parser and `Pillow` offline image manipulation will execute seamlessly in this cloud environment!

---

## 🔒 Security

- **Environment Loaded API Keys:** All API keys are loaded via the `.env` file — never hardcoded.
- **Git Ignore:** Your `.env` and `state.json` databases are explicitly excluded via `.gitignore`.
- **Command Limitations:** Heavy API calls use robust ratelimiting decorators to prevent abuse.
- **Admin Verification:** The `/debug` panel is fully protected by `ADMIN_ID` verification.

> [!IMPORTANT]
> **NEVER** commit your `.env` file to public repositories. If you inadvertently do so, immediately regenerate all affected API keys.

---

## 🛠️ Tech Stack

- **Core Python:** `Python 3.10+`
- **Bot Engine:** `python-telegram-bot`, `asyncio`
- **AI Integration:** `Groq API` (Llama-3.1), `Hugging Face API` (Flux.1)
- **Media Tools:** `yt-dlp` (Downloads), `edge-tts` (Voices), `Pillow` (Stickers)
- **Web Parsing:** `BeautifulSoup4`, standard RSS `ElementTree`
- **Server:** Threaded `HTTPServer` bound to Koyeb Health Checks

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
