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
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создание директорий для данных и изолированного workspace
RUN mkdir -p data/sessions /workspace && chmod 777 /workspace

EXPOSE 5051

ENV DEFAULT_CWD=/workspace
ENV PYTHONUNBUFFERED=1

CMD ["python3", "server.py"]
