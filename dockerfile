FROM python:3.12-slim

WORKDIR /app

# install system dependencies
RUN apt update && apt install -y \
    build-essential \
    libffi-dev \
    git \
    wget \
    && apt clean && rm -rf /var/lib/apt/lists/*

# copy requirements into container
COPY requirements.txt .

# install all heavy packages inside docker
RUN pip install --no-cache-dir -r requirements.txt

# copy your source code
COPY . .

CMD ["python", "main.py"]