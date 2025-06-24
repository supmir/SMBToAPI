FROM python:3

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir Flask==3.1.1 pysmb==1.2.11

COPY app.py .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "app.py"]