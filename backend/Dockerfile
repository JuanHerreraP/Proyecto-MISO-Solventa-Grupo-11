FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home solventa
COPY app ./app
COPY mocks ./mocks
COPY entrypoint.py .
USER solventa
EXPOSE 8000
CMD ["python", "entrypoint.py"]
