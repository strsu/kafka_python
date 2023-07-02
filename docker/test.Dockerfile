FROM python:3.8

RUN apt-get update \
    && apt-get install -y sox \
    && apt-get install -y ffmpeg \
    && apt-get install -y libcairo2 \
    && apt-get install -y libcairo2-dev

COPY ./requirements.txt /
RUN pip install -r ./requirements.txt

WORKDIR /opt/
