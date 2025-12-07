[![Lint](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/lint.yml/badge.svg)](https://github.com/swe-students-fall2025/5-final-sudo/actions/workflows/lint.yml)

# DocKeeper - Document Expiry Tracker

## Description

DocKeeper is a document expiry tracking system designed to help users manage important documents (IDs, permits, subscriptions, warranties, etc.) and receive timely reminders before they expire based on an automated risk calculation. The system runs as **three containers**:

1. **MongoDB**: Shared database for all persisted data.
2. **Web Application**: A Flask-based web interface + REST API for creating and viewing expiring items.
3. **Expiry Reminder Service**: A background worker that periodically scans the database, calculates urgency/risk, and writes the latest computed status back into each item.

All services communicate through MongoDB and are designed to be deployed together.

## Team Members

- [Saud Alsheddy](https://github.com/Saud-Al5)
- [Amy Liu](https://github.com/Amyliu2003)
- [Pranathi Chinthalapani](https://github.com/PranathiChin)
- [William Chan](https://github.com/wc2184)
- [Kazi Hossain](https://github.com/kazisean)

## Docker Images

- **Web App**: TBD (will be published to Docker Hub before submission)
- **Reminder Service**: TBD (will be published to Docker Hub before submission)

## Prerequisites

- Docker + Docker Compose installed
- (Optional) Node.js if running without Docker

## Quick Start (Docker Compose)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd 5-final-sudo
   ```

2. Start all services:
   ```bash
   docker compose up --build
   ```

This starts:
- **MongoDB** on `27017`
- **Web App** on `8000`
- **Reminder Service** running in the background

Stop everything with:
- `docker compose down`

### Logs

- View all logs: `docker compose logs -f`
- View one service: `docker compose logs -f web-app` or `docker compose logs -f reminder-service`

## TailwindCSS

The web app uses TailwindCSS for styling. The CSS is compiled during the Docker build process—no runtime dependencies needed.

### How it works

When you run `docker compose up --build`, the web-app Dockerfile:
1. Installs Tailwind tooling with npm
2. Compiles `web-app/static/css/tailwind.css` → `web-app/static/css/output.css`
3. Copies the compiled CSS into the final image
4. Flask serves the compiled `output.css` file

The compiled `output.css` is gitignored since Docker generates it automatically.

### Running without Docker

If you need to run Flask locally without Docker (not recommended), compile the CSS first:

```bash
npm ci
npx @tailwindcss/cli -i ./web-app/static/css/tailwind.css -o ./web-app/static/css/output.css --minify
```

Node tools are used only to compile CSS. The app runs fully in Python.

## Environment Setup

Docker Compose is already configured with defaults. If you want to override any environment variables locally, you can create a `.env` file:

```bash
cp .env.example .env
```

Right now, this provides all required environment variables for both services. You can customize values in `.env` if needed.

## Environment Variables

DocKeeper is configured through environment variables (via Docker Compose).

### Web App

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://mongodb:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `dockeeper` | MongoDB database name |

### Reminder Service

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://mongodb:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `dockeeper` | MongoDB database name |
| `REMINDER_INTERVAL_SECONDS` | `60` | Interval between reminder checks (in seconds) |

### Local `.env` (optional)

If you want a local `.env` file for Docker Compose, create `.env` in the project root and set values as needed. A reference sample is provided as `.env.example`.

## Database Collections

### `documents`
Stores the “things that expire” users create.

Core fields:
- `doc_type` (string) - canonical type (e.g., `passport`, `subscription`, `other`)
- `label` (string, optional) - user-provided label (like: "Netflix", "Work", "Mom")
- `name` (string) - display name (generated from type + label)
- `category` (string) - internal grouping derived from type
- `expiry_date` (string) - typically `YYYY-MM-DD`
- `renewal_lead_time_days` (int) - reminder window start (overridable)
- `importance` (int) - internal weighting (overridable)
- `notes` (string, optional)

Worker-computed fields (written by the reminder service):
- `last_risk` (string) - `LOW` / `MEDIUM` / `HIGH` / `CRITICAL`
- `last_days_until` (int) - days remaining (negative means expired)
- `last_checked_at` (datetime) - last time worker evaluated this document

## API Endpoints

### Health Check
- `GET /api/health` - service health

### Documents
- `GET /api/documents` - list documents
- `POST /api/documents` - create a document
- `PATCH /api/documents/<doc_id>` - update document details or renewal settings
- `GET /api/documents?include_archived=1` - include archived documents in list
- `POST /api/documents/<doc_id>/renew` - renew/update expiry date (optional importance/lead time)
- `POST /api/documents/<doc_id>/archive` - archive a document
- `POST /api/documents/<doc_id>/unarchive` - unarchive a document
- `DELETE /api/documents/<doc_id>` - delete a document
- `GET /api/documents/calendar.ics` - download an iCalendar (.ics) file with expiry and reminder events
- `GET /api/documents/calendar.ics?include_archived=1` - include archived in calendar export

## Development Notes

This repo is currently designed to be run via Docker Compose will be ran online later.

## Code Quality

Before submitting changes, run linting and formatting checks:

```bash
# From web-app/ or expiry-reminder-service/
pipenv install --dev
pipenv run black --diff --check .
pipenv run pylint --rcfile=../.pylintrc **/*.py
```

**Note:** The `--rcfile=../.pylintrc` tells pylint to use our custom rules from the root directory (this makes sure pylint isn't too strict). The `**/*.py` checks all Python files in the current subsystem.

CI will automatically check these on pull requests.

## License

See [LICENSE](LICENSE) for details.

