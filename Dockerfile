# Use an official lightweight Python runtime
FROM python:3.10-slim

# Set environment variables for optimized execution
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8000

# Set working directory to the standard code root
WORKDIR /code

# Install essential system dependencies (Required for OR-Tools and Psycopg2)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (for layer caching)
COPY backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application source code
COPY backend/app /code/app

# Expose the deployment port
EXPOSE 8000

# Run the FastAPI server using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
