FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN python -m pip install --no-cache-dir mcp==2.3.0 uvicorn==0.54.0 httpx==0.28.1
COPY server.py ./
RUN useradd --uid 10001 --create-home app
USER 10001
EXPOSE 8022
CMD ["python", "server.py"]
