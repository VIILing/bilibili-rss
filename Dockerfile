FROM python:3.10

WORKDIR /app

COPY LICENSE requirements.txt /app/

RUN pip3 install -r requirements.txt

COPY ./src /app/src

WORKDIR /app/src

CMD ["fastapi", "run", "main.py"]
