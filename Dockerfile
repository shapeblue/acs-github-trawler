FROM python:3.9-slim-buster

COPY bin /opt/
RUN pip install pip==20.0.2 --no-cache-dir && pip install docopts pygithub prettytable pygit2 ;apt update && apt install -y git && apt clean ; mkdir /tmp/repo/ && chmod 0555 /tmp/repo ;mv /opt/startup.sh /usr/bin/startup.sh && chmod +x /usr/bin/startup.sh

ENTRYPOINT ["startup.sh"]
