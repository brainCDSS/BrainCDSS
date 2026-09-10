# Cloud Run GPU image. The private model repository is packaged into a wheel
# before submission so GitHub credentials never enter Cloud Build.
FROM python:3.12-slim
WORKDIR /app
COPY requirements/base.txt requirements/base.txt
COPY requirements/gpu.txt requirements/gpu.txt
COPY runtime-wheels/brainon_ai-*.whl /tmp/runtime-wheels/
RUN pip install --no-cache-dir -r requirements/base.txt -r requirements/gpu.txt \
    && pip install --no-cache-dir /tmp/runtime-wheels/brainon_ai-*.whl \
    && rm -rf /tmp/runtime-wheels
COPY . .
EXPOSE 8100
CMD ["python", "-m", "src.api.run"]
