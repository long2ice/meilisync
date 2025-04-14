#!/bin/bash
set -e

mongod --config /mongod.docker.conf > /var/log/yex.log 2>&1 &

# Wait for MongoDB to be ready
until mongosh --eval "print(\"waited for connection\")"
do
    sleep 1
done

mongosh --file /enable-replica-set.js

# keep the container running
tail -f /dev/null
