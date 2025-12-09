[![Lint](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/lint.yml/badge.svg)](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/lint.yml)
[![Web App CI/CD](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/web-app-cicd.yml/badge.svg)](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/web-app-cicd.yml)
[![Reminder Service CI/CD](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/reminder-service-cicd.yml/badge.svg)](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/reminder-service-cicd.yml)

# DocKeeper - Document Expiry Tracker

## Description

DocKeeper is a document expiry tracking system designed to help users manage important documents (IDs, permits, subscriptions, warranties, etc.) and receive timely reminders before they expire based on an automated risk calculation. The system runs as **three containers**:

1. **MongoDB**: Shared database for all persisted data.
2. **Web Application**: A Flask-based web interface + REST API for creating and viewing expiring items.
3. **Expiry Reminder Service**: A background worker that periodically scans the database, calculates urgency/risk, and sends a **weekly action-needed digest** (via email or log) if critical or high-risk items are found.

All services communicate through MongoDB and are designed to be deployed together.

**Live Demo:** http://45.55.224.107/

## Team Members

- [Saud Alsheddy](https://github.com/Saud-Al5)
- [Amy Liu](https://github.com/Amyliu2003)
- [Pranathi Chinthalapani](https://github.com/PranathiChin)
- [William Chan](https://github.com/wc2184)
- [Kazi Hossain](https://github.com/kazisean)

## Docker Images

- **Web App**: [dockeeper-web-app](https://hub.docker.com/r/sa8429/dockeeper-web-app)
- **Reminder Service**: [dockeeper-reminder-service](https://hub.docker.com/r/sa8429/dockeeper-reminder-service)

## Prerequisites

- Docker + Docker Compose installed
- (Optional) Node.js if running without Docker

## Quick Start (Docker Compose)

1. Clone the repository (use HTTPS or SSH from GitHub):
   ```bash
   git clone <repository-url>
   cd 5-final-sudo
   ```

2. Create configuration file:
   ```bash
   cp .env.example .env
   # On Windows: copy .env.example .env
   ```

3. Start all services:
   ```bash
   docker compose up -d --build
   ```

4. Open the Dashboard:
   [http://localhost:8000](http://localhost:8000)

This starts:
- **MongoDB** (internal only)
- **Web App** on `8000`
- **Reminder Service** running in the background

Stop everything with:
- `docker compose down`

### Logs

- View all logs: `docker compose logs -f`
- View one service: `docker compose logs -f web-app` or `docker compose logs -f reminder-service`

**Verifying Mock Emails:**
When `EMAIL_MODE=mock` (default), the reminder service prints digest emails to the logs instead of sending them. To see them:
1. Create a document expiring soon (e.g., tomorrow) to trigger a "High" risk.
2. Watch the logs:
   ```bash
   docker compose logs -f reminder-service
   ```
3. You will see: `=== MOCK EMAIL DIGEST ===`

**Tip: Resetting the 7-Day Email Cooldown**
If you want to force another email (mock or real) immediately:
```bash
# Enter the mongo container
docker compose exec mongodb mongosh dockeeper --eval "db.notification_state.deleteMany({})"
```


## Configuration Setup

For both local development and deployment, you should create a `.env` file to configure secrets and services.

1. **Create the file:**
   ```bash
   # Windows
   copy .env.example .env

   # Mac/Linux
   cp .env.example .env
   ```

2. **Edit `.env`:**
   - **Local:** The defaults work out of the box.
   - **Production:** You **MUST** update `SECRET_KEY` and email settings.
   
   To test out real email sending you must create a brevo account at [brevo's webiste](https://app.brevo.com/) and get an API key from there. Then update the `BREVO_API_KEY` in the `.env` file.

## Environment Variables

DocKeeper is configured through environment variables (via Docker Compose).

### Web App

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://mongodb:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `dockeeper` | MongoDB database name |
| `SECRET_KEY` | `dev-change-me` | Cryptographic key for sessions. Dev default. **Must be changed in production**. |

### Reminder Service

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://mongodb:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `dockeeper` | MongoDB database name |
| `REMINDER_INTERVAL_SECONDS` | `60` | Interval between reminder checks (in seconds) |
| `EMAIL_MODE` | `mock` | `mock` (log only) or `brevo` (send real emails) |
| `BREVO_API_KEY` | - | Brevo API Key (required if mode is `brevo`) |
| `BREVO_SENDER_EMAIL` | - | Sender email address (required if mode is `brevo`) |
| `BREVO_SENDER_NAME` | `DocKeeper` | Sender name for emails |

## Development Notes

This repo is designed to be run via Docker Compose.

## CI/CD (GitHub Actions)

This repo has two separate CI/CD workflows (one per subsystem):

- **web-app-ci-cd**: tests (>=80% coverage), builds & pushes the web-app image to Docker Hub, then deploys to DigitalOcean
- **reminder-service-ci-cd**: tests (>=80% coverage), builds & pushes the reminder-service image to Docker Hub, then deploys to DigitalOcean

## Deployment (DigitalOcean)

Deployment is done via Docker Compose on a DigitalOcean Droplet.

The live site is currently hosted at: http://45.55.224.107/

## TailwindCSS (build-time only)

We use TailwindCSS for styling. **Node/npm is used only to compile CSS** (no Node runtime in production).

### To run with Docker (recommended)

`docker compose up --build` compiles:
`web-app/static/css/tailwind.css` -> `web-app/static/css/output.css`

`output.css` is **not committed** (generated during build).

### To run without Docker (optional) compile CSS manually

```bash
npm ci
npx @tailwindcss/cli -i ./web-app/static/css/tailwind.css -o ./web-app/static/css/output.css --minify
```

## Code Quality (optional local dev)

CI/CD runs tests/coverage automatically via `requirements.txt`.  
If you prefer Pipenv locally, you can run the same checks with before pushing:

```bash
# From web-app/ or expiry-reminder-service/
pipenv install --dev
pipenv run black --diff --check .
pipenv run pylint --rcfile=../.pylintrc **/*.py
pipenv run pytest --cov=. --cov-report=term-missing
```

**Note:** The `--rcfile=../.pylintrc` tells pylint to use our custom rules from the root directory (this makes sure pylint isn't too strict). The `**/*.py` checks all Python files in the current subsystem.

CI will automatically check these on pull requests.

## License

See [LICENSE](LICENSE) for details.

