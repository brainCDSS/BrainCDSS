FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY start.sh .
RUN chmod +x start.sh

ENV PORT=8080

CMD ["./start.sh"]