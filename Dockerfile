# Use official lightweight Python image
FROM python:3.11-slim

# Install system dependencies (ffmpeg and ffprobe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /code

# Copy requirements and install python packages
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application files
COPY . /code

# Grant permissions for running
RUN chmod -R 777 /code

# Expose port (FastAPI default, Hugging Face uses PORT env variable or 7860)
ENV PORT=7860
EXPOSE 7860

# Run FastAPI app with uvicorn, binding to 0.0.0.0 and the dynamic port
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
