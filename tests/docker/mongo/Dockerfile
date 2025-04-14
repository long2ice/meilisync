# This Dockerfile is needed due to enabling replica mode in docker requiring some extra steps 
FROM mongo:8

COPY mongod.docker.conf mongod.docker.conf
COPY run-mongo.sh ./
COPY enable-replica-set.js ./

RUN chmod +x /run-mongo.sh

CMD ./run-mongo.sh
