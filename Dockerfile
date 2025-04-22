FROM docker.io/bitnami/suitecrm:7.14.6-debian-12-r2

RUN openssl genrsa -out /opt/bitnami/suitecrm/Api/V8/OAuth2/private.key 2048
RUN openssl rsa -in /opt/bitnami/suitecrm/Api/V8/OAuth2/private.key -pubout -out /opt/bitnami/suitecrm/Api/V8/OAuth2/public.key
RUN chmod 600 /opt/bitnami/suitecrm/Api/V8/OAuth2/private.key /opt/bitnami/suitecrm/Api/V8/OAuth2/public.key
RUN chown daemon:daemon /opt/bitnami/suitecrm/Api/V8/OAuth2/p*.key
