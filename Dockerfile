#stage 1
FROM python:3.12-slim AS builder

RUN apt-get update

COPY /app/requirements.txt /app/requirements.txt