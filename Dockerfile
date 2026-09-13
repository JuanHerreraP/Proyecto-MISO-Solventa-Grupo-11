FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY servicios ./servicios
COPY adaptadores ./adaptadores

ENV APP_MODULE=servicios.perfilamiento:app
ENV PORT=8000

CMD ["sh", "-c", "uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT}"]