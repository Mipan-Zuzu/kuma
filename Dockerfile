FROM louislam/uptime-kuma:2

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip sqlite3 \
    && pip3 install --no-cache-dir --break-system-packages boto3 \
    && rm -rf /var/lib/apt/lists/*

COPY backup.py /backup.py
COPY start.sh /start.sh

RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]