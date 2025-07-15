# Use Python 3.12 slim image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including kubectl
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    jq \
    && ARCH=$(dpkg --print-architecture) \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/${ARCH}/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (AWS Strands framework)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY static/ ./static/
COPY pyproject.toml .

# Create directories for data storage
RUN mkdir -p /app/data /tmp/analysis_storage

# Create a non-root user to run the application (following EKS best practices)
RUN useradd -m appuser && chown -R appuser:appuser /app /tmp/analysis_storage
USER appuser

# Set environment variables for Strands
ENV PYTHONPATH=/app
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose the port the app runs on
EXPOSE 8000

# Command to run the Strands-based application
CMD ["python", "-m", "src.main"]
