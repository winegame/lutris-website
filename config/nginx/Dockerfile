FROM nginx:latest
RUN rm /etc/nginx/conf.d/default.conf
COPY templates/500.html /srv/
COPY config/nginx/lutris.conf /etc/nginx/conf.d/

ARG APP_USER=root
USER ${APP_USER}:${APP_USER}
