FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.3.3 /uv /bin/uv

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install git
RUN apt-get -y install docker-compose

ADD README.md /app/README.md
ADD common_packages.yaml /app
ADD pyproject.toml /app/pyproject.toml
ADD uv.lock /app/uv.lock
ADD src /app
WORKDIR /app
RUN uv sync --frozen

CMD ["uv", "run", "run.py"]
