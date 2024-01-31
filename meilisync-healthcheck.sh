#!/bin/bash

tables=$(meilisync check 2>&1 | grep 'ERROR' | awk -F '"' '{print $2}' | awk -F '.' '{print $2}')
args=""
if echo "$tables" | grep -q "\w"; then
    for table in $tables; do
        args="$args -t $table"
    done
    meilisync refresh $args 2> /dev/null
    false
else
    true
fi
