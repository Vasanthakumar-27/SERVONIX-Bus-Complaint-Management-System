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

# Run Gunicorn with gevent worker (single worker required for Socket.IO)
CMD ["gunicorn", "-k", "gevent", "-w", "1", "backend.wsgi:app", "--bind", "0.0.0.0:5000"]
