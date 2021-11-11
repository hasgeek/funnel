FROM nginx:latest

RUN rm /etc/nginx/conf.d/default.conf
COPY ./default.conf /etc/nginx/conf.d

USER root

RUN mkdir -p /vol/static
RUN chmod 755 /vol/static


#USER nginx
