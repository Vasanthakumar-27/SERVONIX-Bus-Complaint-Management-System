FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system deps for Pillow/reportlab (minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# Ensure writable data directory for SQLite database
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1

# Expose default port
EXPOSE 5000

# Stay in /app directory and run backend as a module (fixes relative imports)
WORKDIR /app
CMD ["python", "-m", "backend.app"]
