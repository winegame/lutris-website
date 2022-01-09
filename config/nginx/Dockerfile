FROM nginx:latest
RUN rm /etc/nginx/conf.d/default.conf \
 && sed -i 's/user  nginx;/user  root;/g' /etc/nginx/nginx.conf
COPY templates/500.html /srv/
COPY config/nginx/lutris.conf /etc/nginx/conf.d/
