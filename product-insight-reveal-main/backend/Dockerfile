# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Copy .env if present (optional, for local dev)
COPY env_example.txt .env

# Expose port
EXPOSE 8001

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Start the FastAPI app with uvicorn
CMD ["sh", "-c", "PYTHONPATH=. uvicorn backend_api:app --host 0.0.0.0 --port 8001"] 