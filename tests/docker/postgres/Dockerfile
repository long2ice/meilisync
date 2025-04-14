FROM postgres:15

# Install wal2json plugin
RUN apt-get update && apt-get install -y \
    postgresql-server-dev-15 \
    build-essential \
    git \
    && git clone https://github.com/eulerto/wal2json.git /wal2json \
    && cd /wal2json && make && make install \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /wal2json

COPY postgresql.conf /etc/postgresql/
