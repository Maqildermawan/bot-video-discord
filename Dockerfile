FROM python:3.11-slim

# Install Node.js (untuk bypass n-challenge YouTube) dan FFmpeg (untuk merge video & audio)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]