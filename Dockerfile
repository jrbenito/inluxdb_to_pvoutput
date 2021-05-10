FROM python:3.8-alpine
LABEL maintainer="Josenivaldo Benito Jr. <jrbenito@benito.qsl.br>"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./influx2pvoutput.py" ]