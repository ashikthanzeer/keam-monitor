## Context

The repository needs a reliable, unattended monitoring solution for the KEAM allotment page. The implementation must work in GitHub Actions, use GitHub Secrets for Telegram credentials, and remain easy to extend for additional URLs.

## Goals / Non-Goals

**Goals:**
- Monitor a target webpage on a 5-minute cadence.
- Detect changes using normalized visible content and SHA-256 hashing.
- Notify the user through Telegram when content changes.
- Persist state between workflow runs inside the repository.

**Non-Goals:**
- Browser automation or JavaScript rendering.
- A full web dashboard or persistent database.
- Email, SMS, or other notification channels.

## Decisions

- Use Python 3.12 with `requests` and `beautifulsoup4` to keep the solution lightweight and compatible with GitHub-hosted runners.
- Normalize the webpage into meaningful visible text before hashing so incidental markup changes do not trigger false positives.
- Persist the previous hash and content as simple text files in the repository so the workflow can compare state across executions without external services.
- Use GitHub Actions with a `schedule` trigger and `workflow_dispatch` for manual runs.
- Commit the updated state files back to the repository only when the monitor detects a change, avoiding redundant commits on unchanged runs.

## Risks / Trade-offs

- [Dynamic page content] → The monitor uses content normalization and may miss highly dynamic elements that are not visible text; the implementation is designed to be straightforward and easy to extend.
- [Rate limiting or transient failures] → Requests include timeout and retry logic, and failures are logged with explicit error handling.
- [Telegram rate limits] → Notifications are sent only when content changes, preventing duplicate alerts for unchanged runs.

## Migration Plan

1. Add the required Python dependencies and workflow file.
2. Add GitHub Secrets for the Telegram bot token and chat ID.
3. Run the workflow manually once to confirm the initial state is recorded and notifications are delivered.

## Open Questions

- None. The implementation can proceed with the provided requirements and a sensible default URL.
