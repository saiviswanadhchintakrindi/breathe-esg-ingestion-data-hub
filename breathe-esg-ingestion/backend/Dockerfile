FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic needs a SECRET_KEY at build time; use a dummy — it's never exposed
RUN SECRET_KEY=build-time-static-collection-only python manage.py collectstatic --noinput

RUN chmod +x start.sh

CMD ["bash", "start.sh"]

