FROM ubuntu:20.04 AS sphinxbuild
ARG DEBIAN_FRONTEND=noninteractive
RUN sed -i 's/[a-z0-9.-]*\.[cno][oer][mtg]/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential git python3 python3-pip python3-dev \
    && rm -rf /var/lib/apt/lists/*
COPY config/rst_template.txt /docs/rst_template.txt
WORKDIR /docs
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip3 install --no-cache-dir docutils==0.15.2
RUN git clone --depth 1 https://gitee.com/winegame/lutris
RUN rst2html.py --template=rst_template.txt lutris/docs/installers.rst > /docs/installers.html


FROM node:14-slim AS frontend

ARG DEBIAN_FRONTEND=noninteractive
RUN sed -i 's/[a-z0-9.-]*\.[cno][oer][mtg]/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g bower grunt-cli --registry=https://registry.npm.taobao.org
COPY *.json Gruntfile.js .bowerrc /web/
COPY frontend/ /web/frontend/
WORKDIR /web
RUN npm install --registry=https://registry.npm.taobao.org
RUN npm run setup && npm run build
RUN cd /web/frontend/vue/ && npm install --registry=https://registry.npm.taobao.org && npm run build:issues


FROM strycore/lutriswebsite:latest

ENV LC_ALL=C.UTF-8
ENV DB_HOST="localhost"
ENV DJANGO_SETTINGS_MODULE="lutrisweb.settings.production"

ARG APP_USER=django

RUN useradd -ms /bin/bash -d /app django

ADD --chown=django:django . /app
USER ${APP_USER}:${APP_USER}
WORKDIR /app
RUN mkdir media && chown ${APP_USER}:${APP_USER} media
RUN mkdir static && chown ${APP_USER}:${APP_USER} static

COPY ./config /config
COPY --from=sphinxbuild /docs/installers.html /app/templates/docs/
COPY --from=frontend /web/public/ /app/public/
COPY --from=frontend /web/frontend/vue/dist/ /app/frontend/vue/dist/
COPY --from=frontend /web/components/ /app/components/

CMD ["scripts/gunicorn_start.sh"]
