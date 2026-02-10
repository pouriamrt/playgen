# QA Test Suite - Docker Image
# Based on the official Playwright Python image with all browsers pre-installed.

FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

LABEL maintainer="QA Team"
LABEL description="QA test suite with Playwright, pytest, and all browsers"

# Set working directory
WORKDIR /app

# Copy dependency definition first for layer caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy the full test suite
COPY . .

# Create artifact directories
RUN mkdir -p reports screenshots videos traces

# Default entrypoint runs smoke tests with chromium
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["tests/", "-m", "smoke", "--browser", "chromium", "--timeout", "30", \
     "--html=reports/report.html", "--self-contained-html", "--strict-markers", \
     "--tb=short", "-v"]
