FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_link_filter_bot.py .

CMD ["python", "telegram_link_filter_bot.py"]
