FROM python:slim-bookworm

RUN pip install --upgrade pip

COPY requirements.txt /

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install git
RUN apt-get -y install docker-compose

RUN pip install --trusted-host pypi.python.org -v -r /requirements.txt

WORKDIR /release2mqtt

ADD . /release2mqtt

CMD ["python", "-m", "release2mqtt.app"]
