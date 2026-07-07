## Why

The KEAM allotment page changes are time-sensitive and can affect decision-making. A lightweight GitHub Actions based monitor will detect meaningful content updates and alert the user quickly without requiring a laptop to stay on.

## What Changes

- Add a Python-based monitor that fetches the KEAM allotment webpage on a fixed schedule.
- Extract meaningful visible content, compute a SHA-256 fingerprint, and compare it with the previous run.
- Send Telegram notifications when new content is detected, including a summary of the changes.
- Persist the latest hash and content in the repository so future runs can compare against prior state.
- Provide a GitHub Actions workflow that runs every 5 minutes and can be triggered manually.

## Capabilities

### New Capabilities
- `keam-allotment-monitor`: A production-ready monitoring workflow that fetches the KEAM allotment page, detects changes, and notifies via Telegram.

### Modified Capabilities
- None.

## Impact

- New Python runtime dependency set for monitoring and HTML parsing.
- New GitHub Actions workflow and repository state files.
- GitHub Secrets required for Telegram delivery.
