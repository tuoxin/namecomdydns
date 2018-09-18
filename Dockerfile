# 参考https://github.com/jwater7/docker-godaddy-publicip-updater
FROM python
LABEL maintainer "taxin520@gmail.com"

RUN pip install requests
RUN pip install pyyaml

COPY dnsupdate.py /

CMD ["python", "-u", "/dnsupdate.py"]