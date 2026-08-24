# SDK-neutral scaffold; transport command is intentionally not faked.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python","-c","print('NOT_IMPLEMENTED: verify and connect official MCP SDK')"]
