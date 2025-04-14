FROM getmeili/meilisearch:v1.10@sha256:db5c90b14b406d4cee34c5b6dcd4cffe66ef8766534b079b7db97fe145d01a21

# Install jq for easier parsing of api keys
RUN apk update && apk add --no-cache jq

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV MEILI_API_KEYS_FILE=$MEILI_API_KEYS_FILE

ENTRYPOINT ["/entrypoint.sh"]
