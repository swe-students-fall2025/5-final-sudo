# DocKeeper - Document Expiry Tracker

[![Lint](https://github.com/USERNAME/REPO_NAME/actions/workflows/lint.yml/badge.svg)](https://github.com/USERNAME/REPO_NAME/actions/workflows/lint.yml)
[![Web App CI/CD](https://github.com/USERNAME/REPO_NAME/actions/workflows/web-app.yml/badge.svg)](https://github.com/USERNAME/REPO_NAME/actions/workflows/web-app.yml)
[![Reminder Service CI/CD](https://github.com/USERNAME/REPO_NAME/actions/workflows/reminder-service.yml/badge.svg)](https://github.com/USERNAME/REPO_NAME/actions/workflows/reminder-service.yml)

## Description

DocKeeper is a document expiry tracking system designed to help users manage important documents and receive timely reminders before they expire. The system consists of two main subsystems:

1. **Web Application**: A Flask-based web interface that allows users to add, view, and manage documents with expiry dates. The application provides a RESTful API for document management and a web dashboard for visualization.

2. **Expiry Reminder Service**: A background service that continuously monitors documents in the database, computes risk levels based on expiry dates and importance, and generates reminders for documents approaching their expiration.

Both subsystems are containerized and communicate through a shared MongoDB database, making the system scalable and easy to deploy.

## Team Members

- [Your Name](https://github.com/YOUR_USERNAME) - Add your GitHub profile link here

## Docker Images

- **Web App**: [docker.io/USERNAME/dockeeper-web-app](https://hub.docker.com/r/USERNAME/dockeeper-web-app)
- **Reminder Service**: [docker.io/USERNAME/dockeeper-reminder-service](https://hub.docker.com/r/USERNAME/dockeeper-reminder-service)

## Prerequisites

- Docker and Docker Compose installed on your system
- For local development: Python 3.11+ (optional, if running without Docker)

## Quick Start

### Using Docker Compose (Recommended)

The easiest way to run the entire system is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd 5-final-sudo

# Start all services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

This will start:
- **MongoDB** on port `27017`
- **Web App** on port `8000` (accessible at http://localhost:8000)
- **Reminder Service** running in the background

To stop all services:
```bash
docker-compose down
```

To view logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web-app
docker-compose logs -f reminder-service
```

### Running Individual Services

#### Web App

```bash
cd web-app
docker build -t dockeeper-web-app .
docker run -p 8000:8000 \
  -e MONGO_URI=mongodb://localhost:27017 \
  -e MONGO_DB_NAME=dockeeper \
  dockeeper-web-app
```

#### Reminder Service

```bash
cd expiry-reminder-service
docker build -t dockeeper-reminder-service .
docker run \
  -e MONGO_URI=mongodb://localhost:27017 \
  -e MONGO_DB_NAME=dockeeper \
  -e REMINDER_INTERVAL_SECONDS=60 \
  dockeeper-reminder-service
```

## Environment Variables

### Web App

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `dockeeper` | MongoDB database name |

### Reminder Service

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `dockeeper` | MongoDB database name |
| `REMINDER_INTERVAL_SECONDS` | `60` | Interval between reminder checks (in seconds) |

## Configuration Files

### Environment File Example

Create a `.env` file in the project root (not committed to version control):

```env
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=dockeeper

# Reminder Service Configuration
REMINDER_INTERVAL_SECONDS=60
```

### Docker Compose Override

You can also create a `docker-compose.override.yml` file to customize settings for local development:

```yaml
services:
  web-app:
    environment:
      - MONGO_URI=mongodb://mongodb:27017
      - MONGO_DB_NAME=dockeeper
    volumes:
      - ./web-app:/app
    command: python main.py

  reminder-service:
    environment:
      - REMINDER_INTERVAL_SECONDS=30
```

## Database Setup

The MongoDB database is automatically initialized when the container starts. No manual setup is required. The database will be created with the name specified in `MONGO_DB_NAME` (default: `dockeeper`).

### Database Collections

- `documents`: Stores document information with fields:
  - `name`: Document name
  - `category`: Document category
  - `expiry_date`: Expiry date (ISO format string)
  - `importance`: Importance level (1-5)
  - `renewal_lead_time_days`: Days before expiry to send reminders
  - `notes`: Optional notes

## API Endpoints

### Health Check
- `GET /api/health` - Returns service health status

### Documents
- `GET /api/documents` - List all documents
- `POST /api/documents` - Create a new document
- `DELETE /api/documents/<doc_id>` - Delete a document

### Example: Create a Document

```bash
curl -X POST http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "doc_type": "passport",
    "label": "US Passport",
    "expiry_date": "2025-12-31",
    "notes": "Renew before travel"
  }'
```

## Development

### Local Development Setup

1. Install Python dependencies:
```bash
# Web App
cd web-app
pip install -r requirements.txt

# Reminder Service
cd ../expiry-reminder-service
pip install -r requirements.txt
```

2. Start MongoDB (using Docker):
```bash
docker run -d -p 27017:27017 --name mongodb mongo:7
```

3. Run services locally:
```bash
# Terminal 1: Web App
cd web-app
export MONGO_URI=mongodb://localhost:27017
export MONGO_DB_NAME=dockeeper
python main.py

# Terminal 2: Reminder Service
cd expiry-reminder-service
export MONGO_URI=mongodb://localhost:27017
export MONGO_DB_NAME=dockeeper
python -m reminder_service.main
```

### Running Tests

```bash
# Web App tests
cd web-app
pytest tests/ --cov=. --cov-report=html

# Reminder Service tests
cd expiry-reminder-service
pytest tests/ --cov=. --cov-report=html
```

## Project Structure

```
5-final-sudo/
├── web-app/                 # Flask web application
│   ├── main.py             # Application entry point
│   ├── models.py           # Data models
│   ├── routers/            # API routes
│   ├── templates/          # HTML templates
│   ├── tests/              # Unit tests
│   ├── Dockerfile          # Web app container definition
│   └── requirements.txt    # Python dependencies
├── expiry-reminder-service/ # Background reminder service
│   ├── reminder_service/   # Service package
│   │   ├── main.py        # Service entry point
│   │   └── logic.py       # Business logic
│   ├── tests/             # Unit tests
│   ├── Dockerfile         # Service container definition
│   └── requirements.txt   # Python dependencies
├── docker-compose.yml      # Orchestration configuration
├── pyproject.toml          # Project configuration
└── README.md              # This file
```

## License

See [LICENSE](./LICENSE) file for details.
