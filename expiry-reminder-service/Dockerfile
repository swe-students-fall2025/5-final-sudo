FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the reminder_service package
COPY reminder_service/ ./reminder_service/

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app

# Run the reminder service
CMD ["python", "-m", "reminder_service.main"]

