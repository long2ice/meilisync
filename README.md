# meilisync

[![image](https://img.shields.io/pypi/v/meilisync.svg?style=flat)](https://pypi.python.org/pypi/meilisync)
[![image](https://img.shields.io/github/license/meilisync/meilisync)](https://github.com/meilisync/meilisync)
[![image](https://github.com/meilisync/meilisync/workflows/pypi/badge.svg)](https://github.com/meilisync/meilisync/actions?query=workflow:pypi)
[![image](https://github.com/meilisync/meilisync/workflows/ci/badge.svg)](https://github.com/meilisync/meilisync/actions?query=workflow:ci)

## Introduction

Realtime sync data from MySQL/PostgreSQL/MongoDB to Meilisearch.

## Install

Just install from pypi:

```shell
pip install meilisync
```

## Use docker (Recommended)

You can use docker to run `meilisync`:

```yaml
version: "3"
services:
  meilisync:
    image: long2ice/meilisync
    volumes:
      - ./config.yml:/meilisync/config.yml
    restart: always
```

## Prerequisites

- `MySQL`: `binlog_format = ROW`, use binary log.
- `PostgreSQL`: `wal_level = logical` and install `wal2json` extension, use logical replication.
- `MongoDB`: enable replica set mode, use change stream.

## Quick Start

If you run `meilisync` without any arguments, it will try to load the configuration from `config.yml` in the current
directory.

```shell
❯ meilisync --help
                                                                                                                                                                                      
 Usage: meilisync [OPTIONS] COMMAND [ARGS]...                                                                                                                                         
                                                                                                                                                                                      
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --config              -c      TEXT  Config file path [default: config.yml]                                                                                                         │
│ --install-completion                Install completion for the current shell.                                                                                                      │
│ --show-completion                   Show completion for the current shell, to copy it or customize the installation.                                                               │
│ --help                              Show this message and exit.                                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ check            Check whether the data in the database is consistent with the data in Meilisearch                                                                                 │
│ refresh          Refresh all data by swap index                                                                                                                                    │
│ start            Start meilisync                                                                                                                                                   │
│ version          Show meilisync version                                                                                                                                            │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Start sync

Start sync data from MySQL to Meilisearch:

```shell
❯ meilisync start
2023-03-07 08:37:25.656 | INFO     | meilisync.main:_:86 - Start increment sync data from "mysql" to Meilisearch...
```

### Refresh sync

Refresh all data by swap index:

```shell
❯ meilisync refresh -t test
```

### Check sync

Check whether the data in the database is consistent with the data in Meilisearch:

```shell
❯ meilisync check -t test

```

## Configuration

Here is an example configuration file:

```yaml
debug: true
plugins:
  - meilisync.plugin.Plugin
progress:
  type: file
source:
  type: mysql
  host: 192.168.123.205
  port: 3306
  user: root
  password: "123456"
  database: beauty
meilisearch:
  api_url: http://192.168.123.205:7700
  api_key:
  insert_size: 1000
  insert_interval: 10
sync:
  - table: collection
    index: beauty-collections
    plugins:
      - meilisync.plugin.Plugin
    full: true
    fields:
      id:
      title:
      description:
      category:
  - table: picture
    index: beauty-pictures
    full: true
    fields:
      id:
      description:
      category:
sentry:
  dsn: ""
  environment: "production"
```

### debug (optional)

Enable debug mode, default is `false`, if you want to see more logs, you can set it to `true`.

### plugins (optional)

The plugins are used to customize the data before or after insert to Meilisearch and the plugins is a list of python modules.

Which is a python class with `pre_event` and `post_event` methods, the `pre_event` method is called before insert to Meilisearch, the `post_event` method is called after insert to Meilisearch.

```python
class Plugin:
    is_global = False

    async def pre_event(self, event: Event):
        logger.debug(f"pre_event: {event}, is_global: {self.is_global}")
        return event

    async def post_event(self, event: Event):
        logger.debug(f"post_event: {event}, is_global: {self.is_global}")
        return event
```

The `is_global` is used to indicate whether the plugin instance is global, if set to `True`, the plugin instance will be created only once, otherwise, the plugin instance will be created for each event.

### progress

The progress is used to record the last sync position, such as binlog position for MySQL.

- `type`: `file` or `redis`, if set to file, another option `path` is required.
- `path`: the file path to store the progress, default is `progress.json`.
- `key`: the redis key to store the progress, default is `meilisync:progress`.
- `dsn`: the redis dsn, default is `redis://localhost:6379/0`.

### source

Source database configuration, currently only support MySQL and PostgreSQL and MongoDB.

- `type`: `mysql` or `postgres` or `mongo`.
- `server_id`: the server id for MySQL binlog, default is `1`.
- `database`: the database name.
- `other keys`: the database connection arguments, MySQL see [asyncmy](https://github.com/long2ice/asyncmy), PostgreSQL
  see [psycopg2](https://www.psycopg.org/docs/usage.html), MongoDB see [motor](https://motor.readthedocs.io/en/stable/).

### meilisearch

Meilisearch configuration.

- `api_url`: the Meilisearch API URL.
- `api_key`: the Meilisearch API key.
- `insert_size`: insert after collecting this many documents, optional.
- `insert_interval`: insert after this many seconds have passed, optional.

If nether `insert_size` nor `insert_interval` is set, it will insert each document immediately.

If you prefer performance, just set and increase `insert_size` and `insert_interval`. The insert will be made as long as
one of the conditions is met.

### sync

The sync configuration, you can add multiple sync tasks.

- `table`: the database table name or collection name.
- `index`: the Meilisearch index name, if not set, it will use the table name.
- `full`: whether to do a full sync, default is `false`.
- `fields`: the fields to sync, if not set, it will sync all fields. The key is table field name, the value is the
  Meilisearch field name, if not set, it will use the table field name.
- `plugins`: the table level plugins, optional.

### sentry (optional)

Sentry configuration.

- `dsn`: the sentry dsn.
- `environment`: the sentry environment, default is `production`.

## License

This project is licensed under the
[Apache-2.0](https://github.com/meilisync/meilisync/blob/main/LICENSE) License.
