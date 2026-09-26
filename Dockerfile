FROM python:3.9-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Koyeb exposes the lowest exposed port as PORT when not set manually.
EXPOSE 8000

CMD ["python3", "main.py"]
