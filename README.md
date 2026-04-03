# Lucifer — AI-Powered Telegram Bot

A modular, multi-feature Telegram bot built with Python. Lucifer combines AI chat, image generation, deal hunting, and live weather — all in one bot.

---

## Features

| Feature | Description |
|:---|:---|
| **AI Chat (Vision)** | Chat with Llama 4 Scout via Groq — supports text AND image analysis |
| **AI Image Generation** | Generate stunning AI art with Stable Diffusion XL via Hugging Face |
| **Daraz Deal Finder** | Search for the best product deals on Daraz.com.bd |
| **Live Weather** | Check real-time weather for any city worldwide |
| **Admin Debug Panel** | Monitor API health, uptime, and toggle services on/off |

---

## Project Structure

```
my_telegram_bot/
├── main.py              # Entry point — starts the bot + health check server
├── config.py            # Loads environment variables securely
├── state.py             # Manages API on/off state (admin feature)
├── Procfile             # Deployment config for Koyeb
├── requirements.txt     # Python dependencies
├── .env.example         # Template for environment variables
│
├── handlers/            # Telegram command & message handlers
│   ├── basic.py         # /start, AI chat, button callbacks
│   ├── image_gen.py     # /image command
│   ├── daraz_handler.py # /find command
│   ├── weather.py       # /weather command
│   └── debug.py         # /debug admin panel
│
├── services/            # Business logic & API integrations
│   ├── ai_chat.py       # Groq / Llama 4 Scout integration
│   ├── image_gen.py     # Hugging Face Stable Diffusion
│   ├── daraz_service.py # Daraz web scraping
│   └── weather.py       # OpenWeatherMap API
│
└── utils/
    └── logger.py        # Centralized logging
```

---

## Quick Start (Local)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Telegram_Bot-Lucifer.git
cd Telegram_Bot-Lucifer
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

Open `.env` and fill in your real API keys:

| Key | Where to Get It |
|:---|:---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com/) |
| `IMAGE_GEN_KEY` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `OPENWEATHERMAP_API_KEY` | [openweathermap.org/api](https://openweathermap.org/api) |
| `ADMIN_ID` | Send /debug to your bot to see your Telegram User ID |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) (optional) |

### 5. Run the Bot

```bash
python main.py
```

---

## Deploy to Koyeb (Free, 24/7)

Koyeb provides free hosting with no credit card needed.

### Step 1: Push to GitHub
Make sure your code is on GitHub (your .env is safely excluded by .gitignore).

### Step 2: Create a Koyeb Account
Sign up at [koyeb.com](https://www.koyeb.com/) — no credit card required.

### Step 3: Create a New Service
1. Click "Create Service" → "GitHub"
2. Connect your GitHub account and select this repository
3. Set the Builder to Buildpack
4. Set the Run command to python main.py
5. Set the Port to 8000

### Step 4: Add Environment Variables
In the Koyeb service settings, add each key from .env.example as an environment variable. Never paste keys in code — always use the dashboard.

### Step 5: Deploy
Click Deploy — Koyeb will build and start your bot automatically. It runs 24/7.

---

## Security

- All API keys are loaded from environment variables (.env) — never hardcoded.
- .env is excluded from Git via .gitignore — it will never be uploaded.
- Admin commands (/debug, toggle APIs) are protected by ADMIN_ID verification.
- When deploying, always use the hosting platform's Environment Variables dashboard.

> [!IMPORTANT]
> **NEVER** commit your .env file to GitHub. If you accidentally do, **immediately regenerate all your API keys**.

---

## Tech Stack

- **Language:** Python 3.10+
- **Bot Framework:** [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- **AI Chat:** [Groq](https://groq.com/) (Llama 4 Scout — Multimodal)
- **Image Gen:** [Hugging Face](https://huggingface.co/) (Stable Diffusion XL)
- **Weather:** [OpenWeatherMap](https://openweathermap.org/)
- **Hosting:** [Koyeb](https://koyeb.com/) (Free Tier)

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
