FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.3.3 /uv /bin/uv

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install git
RUN apt-get -y install docker-compose

ADD README.md .
ADD pyproject.toml .
ADD uv.lock .
ADD src /release2mqtt
RUN uv sync --frozen

WORKDIR /release2mqtt

CMD ["uv", "run", "release2mqtt"]
