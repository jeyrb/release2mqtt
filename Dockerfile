FROM python:3.11-slim-bullseye

RUN pip install --upgrade pip

COPY requirements.txt /

RUN apt-get -y update
RUN apt-get -y upgrade

RUN pip install --trusted-host pypi.python.org -v -r /requirements.txt

WORKDIR /release2mqtt

ADD . /release2mqtt

CMD ["python", "-u", "app.py"]
