# CPU API image; worker/GPU dependencies use an approved separate deployment layer.
FROM python:3.12-slim
WORKDIR /app
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt
COPY . .
EXPOSE 8100
CMD ["uvicorn","src.api.main:app","--host","0.0.0.0","--port","8100"]
