FROM python:3.9.13-slim

RUN pip install -U pip
RUN pip install pipenv
RUN apt-get update -y && apt-get install -y gcc

WORKDIR /app

COPY [ "Pipfile", "Pipfile.lock",  "./"]
COPY [ "app.py", "model.bin",  "./"]

RUN pipenv install --system --deploy

EXPOSE 9696

ENTRYPOINT [ "gunicorn", "--bind=0.0.0.0:9696", "--timeout=600", "app:app" ]
