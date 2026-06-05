FROM python:3.11-slim

WORKDIR /app

COPY Bot/requirements.txt ./bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt

COPY Bot/ ./bot/

CMD ["python", "bot/query_bot.py"]
