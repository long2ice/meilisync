#!/bin/sh
# Waits for meilisearch to start, then adds the api keys to disk for easier copying
set -e

echo "Starting MeiliSearch..."
meilisearch --master-key "${MEILI_MASTER_KEY}" &
MEILI_PID=$!

echo "Waiting for MeiliSearch to be healthy..."
while true; do
  if curl -s http://0.0.0.0:7700/health | grep -q '"status":"available"'; then
    break
  fi
  sleep 1
done

echo "MeiliSearch is healthy."


if [ ! -f "$MEILI_API_KEYS_FILE" ]; then
  echo "Key file not found. Retrieving default search API key..."
  sleep 2
  keys=$(curl -s -H "Authorization: Bearer ${MEILI_MASTER_KEY}" http://0.0.0.0:7700/keys)
  pretty_json=$(echo "$keys" | jq .)
  
  if [ -n "$pretty_json" ] && [ "$pretty_json" != "null" ]; then
    echo "$pretty_json" > "$MEILI_API_KEYS_FILE"
    echo "API Keys written to $MEILI_API_KEYS_FILE"
  else
    echo "Failed to retrieve API keys."
  fi
else
  echo "Key file already exists at $MEILI_API_KEYS_FILE. Skipping key retrieval."
fi

# Wait for the MeiliSearch process so the container doesn't exit
wait $MEILI_PID
