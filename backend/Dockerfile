# Use an official lightweight Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency requirements first to optimize build caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend as a Python package so relative imports are reliable.
COPY . ./backend

# Expose port 8080 for Cloud Run contract compliance
EXPOSE 8080

# Run the backend app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
