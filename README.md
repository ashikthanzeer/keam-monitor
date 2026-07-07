# KEAM Allotment Monitor

This repository contains a production-ready Python monitor for the KEAM allotment page at `https://cee.kerala.gov.in/keam2026/allotlist`.

The monitor:
- fetches the page every 5 minutes,
- strips non-visible and dynamic HTML elements,
- computes a SHA-256 fingerprint of the meaningful content,
- compares it with the previous run,
- sends a Telegram alert only when the page content changes.

## Repository structure

```text
.
├── monitor.py
├── requirements.txt
├── README.md
├── .gitignore
├── last_hash.txt
├── last_content.txt
└── .github/
    └── workflows/
        └── monitor.yml
```

## Installation

1. Clone the repository.
2. Create and activate a Python 3.12 virtual environment.
3. Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Telegram bot setup

1. Open Telegram and start a chat with BotFather.
2. Send `/newbot` and follow the prompts.
3. Copy the bot token provided by BotFather.

## Obtain your Telegram Chat ID

1. Start a chat with your new bot.
2. Send any message to the bot.
3. Open the browser and visit:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

4. In the JSON response, find the `chat.id` value.

## Add GitHub Secrets

In GitHub repository settings, go to Secrets and variables → Actions and add:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Running locally

Run the monitor directly:

```bash
python monitor.py
```

To test a different URL locally, set this environment variable:

```bash
MONITOR_URL="https://example.com" python monitor.py
```

The monitor also supports multiple URLs via `MONITOR_URLS`, using comma-separated values.

## GitHub Actions deployment

The workflow `.github/workflows/monitor.yml` is configured to:
- run every 5 minutes,
- install dependencies,
- execute `monitor.py`,
- commit updated state files when content changes.

Make sure the repository is on the default branch before relying on auto-commit behavior.

## What files are stored

- `last_hash.txt`: the SHA-256 hash of the last observed page content.
- `last_content.txt`: the normalized page text used for diffing.

These files are committed back to the repository when a content change is detected.

## Troubleshooting

- `Missing Telegram credentials`: verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set.
- `HTTP error while fetching`: the monitored site returned a non-2xx response.
- `Network error while fetching`: the runner could not reach the site.
- `No notification sent`: this can happen on the first run, when the baseline is being initialized.

## Extending the monitor

The project is built with modular functions and session retry logic so it can be extended later to support monitoring multiple URLs and more advanced diffing.
