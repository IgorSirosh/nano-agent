FROM python:3.11-slim

WORKDIR /app

# Установка базовых утилит Linux для bash-агента
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    ca-certificates \
    procps \
    git \
    jq \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создание директории данных
RUN mkdir -p data/sessions

EXPOSE 5051

CMD ["python3", "server.py"]
