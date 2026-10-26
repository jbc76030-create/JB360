FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN groupadd --gid 10001 jb360 && useradd --uid 10001 --gid 10001 --no-create-home jb360 \
    && mkdir -p /data && chown 10001:10001 /data
USER 10001:10001

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
