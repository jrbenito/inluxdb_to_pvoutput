FROM python:3.9-alpine as base

# Install requirements
FROM base as builder

RUN mkdir /install
WORKDIR /install

COPY requirements.txt /requirements.txt
RUN pip install --prefix=/install -r /requirements.txt

# Prepare app
FROM base

COPY --from=builder /install /usr/local
COPY src/*.py /app/

WORKDIR /app

CMD [ "python", "./influx2pvoutput.py" ]