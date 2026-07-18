FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/clipnotes

COPY pyproject.toml README.md ./
COPY clipnotes ./clipnotes
RUN pip install --no-cache-dir .

RUN useradd --create-home clipnotes
USER clipnotes

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

CMD ["uvicorn", "clipnotes.main:app", "--host", "0.0.0.0", "--port", "8000"]
