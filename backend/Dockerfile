# Django API image; migration execution remains an explicit operator step.
FROM python:3.12-slim
WORKDIR /app
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8080"]

