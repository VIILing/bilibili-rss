FROM python:3.10

WORKDIR /app

COPY ./src /app/src
COPY LICENSE requirements.txt /app/

RUN pip3 install -r requirements.txt

WORKDIR /app/src

CMD ["fastapi", "run", "main.py"]
