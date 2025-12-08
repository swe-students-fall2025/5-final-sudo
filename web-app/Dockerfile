# UI build stage (Tailwind)
FROM node:20-alpine AS ui
WORKDIR /ui

COPY package.json package-lock.json ./
RUN npm ci

# Copy only what Tailwind needs to scan/build
COPY web-app/templates ./web-app/templates
COPY web-app/static ./web-app/static

# Build output.css (Tailwind v4 CLI)
RUN npx @tailwindcss/cli \
    -i ./web-app/static/css/tailwind.css \
    -o ./web-app/static/css/output.css \
    --minify \
    --content "./web-app/templates/**/*.html,./web-app/static/js/**/*.js"


# Python runtime stage
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY web-app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY web-app/ ./
COPY --from=ui /ui/web-app/static/css/output.css ./static/css/output.css

EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "main:app"]

