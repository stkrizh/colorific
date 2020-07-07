FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN mkdir /app

COPY ./requirements /app/requirements

RUN pip install -r /app/requirements/main.txt

COPY . /app

WORKDIR /app

EXPOSE 8080

CMD ["python", "-m", "colorific"]
