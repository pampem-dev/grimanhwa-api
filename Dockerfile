FROM python:3.11-slim

# Install Chromium and Chromium Driver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 \
    libatk1.0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgtk-3-0 \
    libgbm1 \
    libasound2t64 \
    libmariadb-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables for Selenium
ENV PATH="/usr/bin/chromedriver:${PATH}"

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi"]
