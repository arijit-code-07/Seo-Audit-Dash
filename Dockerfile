FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY seo_auditor.py .
COPY app.py .
COPY dashboard.html .

# Expose port for web dashboard
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
