## ADDED Requirements

### Requirement: Monitor the KEAM allotment page
The system SHALL fetch the configured webpage at regular intervals, normalize the visible content, and compare it with the previous run to detect meaningful changes.

#### Scenario: Initial state capture
- **WHEN** the monitor runs for the first time
- **THEN** it SHALL store the current hash and content as the baseline state.

#### Scenario: No change detected
- **WHEN** the normalized content has not changed since the previous run
- **THEN** the system SHALL exit successfully without sending a notification.

#### Scenario: Change detected
- **WHEN** the normalized content changes from the previous run
- **THEN** the system SHALL persist the new state and prepare a Telegram notification with a change summary.

### Requirement: Send Telegram alerts
The system SHALL send a Telegram message containing the alert title, timestamp in IST, monitored URL, change summary, and a few representative changed lines when a content change is detected.

#### Scenario: Telegram notification
- **WHEN** a meaningful change is detected and Telegram credentials are configured
- **THEN** the system SHALL send a Telegram message to the configured chat.

#### Scenario: Missing Telegram credentials
- **WHEN** Telegram credentials are missing
- **THEN** the system SHALL log a warning and continue without failing the run.

### Requirement: Handle network and HTTP failures
The system SHALL retry transient network failures, respect request timeouts, detect HTTP errors, and report them through logs and optional Telegram alerts.

#### Scenario: Transient request failure
- **WHEN** a request fails due to a temporary network issue
- **THEN** the system SHALL retry before reporting a failure.

#### Scenario: HTTP error response
- **WHEN** the target page returns an HTTP error status
- **THEN** the system SHALL log the error and surface it in the run output.
