FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir prometheus-client

COPY exporter.py /app/

EXPOSE 9092

CMD python /app/exporter.py --db-path $DB_PATH --port 9092
