# ePub to Audiobook Converter - Docker Image
# Uses espeak-ng for TTS (traditional, non-neural)

FROM python:3.11-slim

LABEL maintainer="epub2audiobook"
LABEL description="Convert ePub files to audiobooks using traditional TTS"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # TTS engine
    espeak-ng \
    espeak-ng-data \
    libespeak-ng1 \
    # Audio processing
    ffmpeg \
    libavcodec-extra \
    # Build dependencies
    gcc \
    python3-dev \
    # Health check
    curl \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user (non-root)
RUN useradd -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt requirements-web.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

# Copy application code
COPY core/ ./core/
COPY tts/ ./tts/
COPY audio/ ./audio/
COPY web/ ./web/

# Create data directories
RUN mkdir -p /data/uploads /data/output /data/db && \
    chown -R appuser:appuser /app /data

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "600", "web.app:app"]
