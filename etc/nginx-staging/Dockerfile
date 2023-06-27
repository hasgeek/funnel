FROM nginx:latest

RUN rm /etc/nginx/conf.d/default.conf
COPY ./default.conf /etc/nginx/conf.d
COPY ./uwsgi_params /etc/nginx/uwsgi_params

USER root

RUN mkdir -p /vol/static
RUN chmod 755 /vol/static


#USER nginx
