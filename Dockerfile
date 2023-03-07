FROM node:lts

ENV LANG=C.UTF-8

RUN DEBIAN_FRONTEND=non-interactive && \
    mkdir /logs && \
    apt-get -y update && \
    apt-get -y install software-properties-common gcc && \
    apt-get -y install python3 python3-pip python3-distutils python3-apt && \
    apt-get -y install curl && \
    groupadd -r -g 55020 appuser && \
    useradd -u 55020 -g 55020 --create-home appuser

WORKDIR /home/appuser/epadd-curator-app

COPY . /home/appuser/epadd-curator-app

RUN chown appuser:appuser -R /home/appuser && \
    chown appuser:appuser -R /logs

USER appuser
# Append SAN section to openssl.cnf and generate a new self-signed certificate and key
RUN mkdir -p /home/appuser/ssl/certs && \
    cp /etc/ssl/openssl.cnf /home/appuser/ssl/openssl.cnf && \
    printf "[SAN]\nsubjectAltName=DNS:*.hul.harvard.edu,DNS:*.lts.harvard.edu" >> /home/appuser/ssl/openssl.cnf && \
    openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 -subj "/C=US/ST=Massachusetts/L=Cambridge/O=Library Technology Services/CN=*.lib.harvard.edu" -extensions SAN -reqexts SAN -config /home/appuser/ssl/openssl.cnf -keyout /home/appuser/ssl/certs/server.key -out /home/appuser/ssl/certs/server.crt

RUN npm install && \
    python3 -m pip install -U pip && \
    python3 -m pip install -r requirements.txt && \
    chmod +x /home/appuser/epadd-curator-app/scripts/monitor_epadd_exports.py && \
    chmod +x /home/appuser/epadd-curator-app/scripts/test_export.py

CMD ["npm", "start"]
