# KEAM Allotment Monitor

This repository contains a production-ready Python monitor for the KEAM allotment page at https://cee.kerala.gov.in/keam2026/allotlist.

The refactored service now:
- fetches the page on a scheduled cadence,
- extracts meaningful allotment-related content instead of hashing the full page,
- detects added or removed PDFs, links, and title changes,
- sends Telegram alerts with Markdown formatting,
- stores monitor state in JSON for future runs.

## Repository structure

```text
.
├── main.py
├── monitor.py
├── requirements.txt
├── README.md
├── .gitignore
├── state.json
├── keam_monitor/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── monitor.py
│   ├── parser.py
│   ├── storage.py
│   ├── telegram.py
│   └── utils.py
└── .github/workflows/monitor.yml
```

## Installation

1. Clone the repository.
2. Create and activate a Python 3.12+ virtual environment.
3. Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Telegram bot setup

1. Open Telegram and start a chat with BotFather.
2. Send /newbot and follow the prompts.
3. Copy the bot token provided by BotFather.

## Obtain your Telegram chat ID

1. Start a chat with your new bot.
2. Send any message to the bot.
3. Open the browser and visit:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

4. In the JSON response, find the chat.id value.

## Add GitHub secrets

In GitHub repository settings, open Secrets and variables → Actions and add:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## Running locally

Run the monitor directly:

```bash
python main.py
```

To test a different URL locally, set this environment variable:

```bash
MONITOR_URL="https://example.com" python main.py
```

The monitor also supports multiple URLs via MONITOR_URLS, using comma-separated values.

## GitHub Actions deployment

The workflow in .github/workflows/monitor.yml is configured to:
- run every 5 minutes,
- install dependencies,
- execute the modular monitor entrypoint,
- commit updated state.json content when a change is detected.

## State storage

State is written to state.json and stored per URL with fields such as hash, content, links, pdfs, titles, last_checked, and last_changed.

## Troubleshooting

- Missing Telegram credentials: verify TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.
- HTTP error while fetching: the monitored site returned a non-2xx response.
- Network error while fetching: the runner could not reach the site.
- No notification sent: this can happen on the first run, when the baseline is being initialized.

## Extending the monitor

The project is structured around small modules so it can later support multiple users, interactive Telegram commands, a database layer, or a FastAPI service without major rewrites.
