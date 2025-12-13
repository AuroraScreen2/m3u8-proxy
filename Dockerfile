# Get the official image that already includes Python + Browsers
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
COPY main.py .

# Install python libraries
RUN pip install --no-cache-dir -r requirements.txt

# Open port 8080
EXPOSE 8080

# Run the app
CMD ["python", "main.py"]
