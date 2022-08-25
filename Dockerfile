FROM node:lts

ENV LANG=C.UTF-8

RUN DEBIAN_FRONTEND=non-interactive && \
    mkdir /logs && \
    apt-get -y update && \
    apt-get -y install software-properties-common gcc && \
    apt-get -y install python3 python3-pip python3-distutils python3-apt && \
    groupadd -r -g 55020 appuser && \
    useradd -u 55020 -g 55020 --create-home appuser

WORKDIR /home/appuser/epadd-curator-app

COPY . /home/appuser/epadd-curator-app

RUN chown appuser:appuser -R /home/appuser && \
    chown appuser:appuser -R /logs

USER appuser

RUN npm install && \
    python3 -m pip install -U pip && \
    python3 -m pip install -r requirements.txt && \
    chmod +x /home/appuser/epadd-curator-app/scripts/monitor_epadd_exports.py && \
    chmod +x /home/appuser/epadd-curator-app/scripts/test_export.py

CMD ["npm", "start"]
