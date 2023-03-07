# meilisync

[![image](https://img.shields.io/pypi/v/meilisync.svg?style=flat)](https://pypi.python.org/pypi/meilisync)
[![image](https://img.shields.io/github/license/meilisync/meilisync)](https://github.com/meilisync/meilisync)
[![image](https://github.com/meilisync/meilisync/workflows/pypi/badge.svg)](https://github.com/meilisync/meilisync/actions?query=workflow:pypi)
[![image](https://github.com/meilisync/meilisync/workflows/ci/badge.svg)](https://github.com/meilisync/meilisync/actions?query=workflow:ci)

## Introduction

Realtime sync data from MySQL/PostgreSQL/MongoDB to meilisearch.

## Install

Just install from pypi:

```shell
pip install meilisync
```

## Use docker (Recommended)

You can use docker to run `meilisync`:

```yaml
version: '3'
services:
  meilisync:
    image: long2ice/meilisync
    volumes:
      - ./config.yml:/meilisync/config.yml
    restart: always
```

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
│ check            Check whether the data in the database is consistent with the data in MeiliSearch                                                                                 │
│ refresh          Delete all data in MeiliSearch and full sync                                                                                                                      │
│ start            Start meilisync                                                                                                                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Start sync

Start sync data from MySQL to MeiliSearch:

```shell
❯ meilisync start
2023-03-07 08:37:25.656 | INFO     | meilisync.main:_:86 - Start increment sync data from "mysql" to MeiliSearch...
```

### Refresh sync

Delete all data in MeiliSearch and full sync:

```shell
❯ meilisync refresh -t test
```

### Check sync

Check whether the data in the database is consistent with the data in MeiliSearch:

```shell
❯ meilisync check -t test

```

## Configuration

Here is an example configuration file:

```yaml
debug: true
progress:
  type: file
source:
  type: mysql
  host: 192.168.123.205
  port: 3306
  user: root
  password: '123456'
  database: beauty
meilisearch:
  api_url: http://192.168.123.205:7700
  api_key:
sync:
  - table: collection
    index: beauty-collections
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
  dsn: ''
  environment: 'production'
```

### debug (optional)

Enable debug mode, default is `false`, if you want to see more logs, you can set it to `true`.

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

MeiliSearch configuration.

- `api_url`: the MeiliSearch API URL. This can be set from the `MEILI_HTTP_ADDR` environment variable.
- `api_key`: the MeiliSearch API key. This can be set with the `MEILI_MASTER_KEY` environment varable.

### sync

The sync configuration, you can add multiple sync tasks.

- `table`: the database table name or collection name.
- `index`: the MeiliSearch index name, if not set, it will use the table name.
- `full`: whether to do a full sync, default is `false`.
- `fields`: the fields to sync, if not set, it will sync all fields. The key is table field name, the value is the
  MeiliSearch field name, if not set, it will use the table field name.

### sentry (optional)

Sentry configuration.

- `dsn`: the sentry dsn.
- `environment`: the sentry environment, default is `production`.

## License

This project is licensed under the
[Apache-2.0](https://github.com/meilisync/meilisync/blob/main/LICENSE) License.
