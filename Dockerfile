FROM python:3.11-slim
WORKDIR /app
COPY src/main.py .
RUN pip install --no-cache-dir Flask requests Flask-Cors gunicorn
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--log-level", "info", "--access-logfile", "-", "main:app"]
