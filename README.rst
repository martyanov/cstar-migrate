cstar-migrate
=============

.. start-inclusion-marker-do-not-remove

.. image:: https://github.com/martyanov/cstar-migrate/workflows/CI/badge.svg?event=push
   :alt: Build Status
   :target: https://github.com/martyanov/cstar-migrate/actions?query=event%3Apush+branch%3Amaster+workflow%3ACI

.. image:: https://img.shields.io/pypi/v/cstar-migrate.svg
   :alt: PyPI Version
   :target: https://pypi.python.org/pypi/cstar-migrate

.. image:: https://img.shields.io/pypi/pyversions/cstar-migrate.svg
   :alt: Supported Python Versions
   :target: https://pypi.python.org/pypi/cstar-migrate

.. image:: https://img.shields.io/pypi/l/cstar-migrate.svg
   :alt: License
   :target: https://pypi.python.org/pypi/cstar-migrate

Cassandra schema migration tool, a fork of `cassandra-migrate`_.

Installation
------------

Run ``python -m pip install cstar-migrate``.

Reasoning
---------

Unlike other available tools, this one:

- Written in Python for easy installation
- Does not require ``cqlsh``, just the Cassandra Python driver
- Supports baselining existing database to given versions
- Supports partial advancement
- Supports locking for concurrent instances using Lightweight Transactions
- Verifies stored migrations against configured migrations
- Stores content, checksum, date and state of every migration
- Supports deploying with different keyspace configurations for different environments
- Supports cql and python scripts migrations

Configuration
-------------

Databases are configured through YAML files. For example:

.. code:: yaml

    keyspace: cstar
    profiles:
      prod:
        replication:
          class: SimpleStrategy
          replication_factor: 3
    migrations_path: ./migrations

Where the ``migrations`` folder (relative to the config file). contains
``.cql`` or ``.py`` files. The files are loaded in lexical order.

The default convention is to name them in the form: ``001_my_migration.{cql | py}``.
A custom naming scheme can be specified with the ``new_migration_name`` option.

For example

.. code:: yaml

    # Default migration names
    new_migration_name: "{next_version:03d}_{desc}"

    # Date-based migration names
    new_migration_name: "{date:YYYYMMDDHHmmss}_{desc}"

    # Custom initial migration content for cql scripts
    new_cql_migration_text: |
      /* Cassandra migration for keyspace {keyspace}.
         Version {next_version} - {date}

         {full_desc} */

    # Custom initial migration content for python scripts
    new_python_migration_text: |
      # Cassandra migration for keyspace {keyspace}.
      # Version {next_version} - {date}
      # {full_desc} */

      def execute(session, **kwargs):
          """
          Main method for your migration. Do not rename this method.

          Raise an exception of any kind to abort the migration.
          """

          print("Cassandra session: ", session)


``new_migration_name`` is a new-style Python format string, which can use the
following parameters:

- ``next_version``: Number of the newly generated migration (as an ``int``).
- ``desc``: filename-clean description of the migration, as specified
  by the user.
- ``full_desc``: unmodified description, possibly containing special characters.
- ``date``: current date in UTC. Pay attention to the choice of formatting,
  otherwise you might include spaces in the file name. The above example should
  be a good starting point.
- ``keyspace``: name of the configured keyspace.

The format string should *not* contain the .cql or .py extensions, as it they
added automatically.

``new_cql_migraton_text`` defines the initial content of CQL migration files.

``new_python_migraton_text`` defines the initial content of Python migration
files.


Profiles
--------

Profiles can be defined in the configuration file. They can configure
the ``replication`` and ``durable_writes`` parameters for
``CREATE KEYSPACE``. A default ``dev`` profile is implicitly defined
using a replication factor of 1.

Usage
-----

Common parameters:

::

  -H HOSTS, --hosts HOSTS
                        Comma-separated list of contact points
  -p PORT, --port PORT
                        Connection port
  -u USER, --user USER
                        Connection username
  -P PASSWORD, --password PASSWORD
                        Connection password
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Path to configuration file
  -l PROTOCOL_VERSION, --protocol-version PROTOCOL_VERSION
                        Connection protocol version
  -m PROFILE, --profile PROFILE
                        Name of keyspace profile to use
  -s SSL_CERT, --ssl-cert SSL_CERT
                        File path of .pem or .crt containing certificate of
                        the cassandra host you are connecting to (or the
                        certificate of the CA that signed the host
                        certificate). If this option is provided, cassandra-
                        migrate will use ssl to connect to the cluster. If
                        this option is not provided, the -k and -t options
                        will be ignored.
  -k SSL_CLIENT_PRIVATE_KEY, --ssl-client-private-key SSL_CLIENT_PRIVATE_KEY
                        File path of the .key file containing the private key
                        of the host on which the cstar-migrate command is
                        run. This option must be used in conjuction with the
                        -t option. This option is ignored unless the -s option
                        is provided.
  -t SSL_CLIENT_CERT, --ssl-client-cert SSL_CLIENT_CERT
                        File path of the .crt file containing the public
                        certificate of the host on which the cstar-migrate
                        command is run. This certificate (or the CA that
                        signed it) must be trusted by the cassandra host that
                        migrations are run against. This option must be used
                        in conjuction with the -k option. This option is
                        ignored unless the -s option is provided.
  -y, --assume-yes
                        Automatically answer "yes" for all questions

migrate
~~~~~~~

Advances a database to the latest (or chosen) version of migrations.
Creates the keyspace and migrations table if necessary.

Migrate will refuse to run if a previous attempt failed. To override
that after cleaning up any leftovers (as Cassandra has no DDL
transactions), use the ``--force`` option.

Examples:

.. code:: bash

    # Migrate to the latest database version using the default configuration file,
    # connecting to Cassandra in the local machine
    cstar-migrate -H 127.0.0.1 migrate

    # Migrate to version 2 using a specific config file
    cstar-migrate -c mydb.yml migrate 2

    # Migrate to a version by name
    cstar-migrate migrate 002_my_changes.cql

    # Force migration after a failure
    cstar-migrate migrate 2 --force

reset
~~~~~

Reset the database by dropping an existing keyspace, then running a migration.

Examples:

.. code:: bash

    # Reset the database to the latest version
    cstar-migrate reset

    # Reset the database to a specifis version
    cstar-migrate reset 3

clear
~~~~~

Clear the database by dropping an existing keyspace.

Example:

.. code:: bash

    # Clear the database
    cstar-migrate clear

baseline
~~~~~~~~

Advance an existing database version without actually running the
migrations.

Useful for starting to manage a pre-existing database without recreating
it from scratch.

Examples:

.. code:: bash

    # Baseline the existing database to the latest version
    cstar-migrate baseline

    # Baseline the existing database to a specific version
    cstar-migrate baseline 5

status
~~~~~~

Print the current status of the database.

Example:

.. code:: bash

    cstar-migrate status

generate
~~~~~~~~

Generate a new migration file with the appropriate name and a basic header
template, in the configured ``migrations_path``.

When running the command interactively, the file will be opened by the default
editor. The newly-generated file name will be printed to stdout.

To generate a Python script, specify the ``--python`` option.

See the configuration section for details on migration naming.

Examples:

.. code:: bash

    cstar-migrate generate "My migration description"

    cstar-migrate generate "My migration description" --python

.. _cassandra-migrate: https://github.com/Cobliteam/cassandra-migrate
