import codecs
import functools
import importlib
import itertools
import logging
import os
import re
import sys
import uuid

import arrow
import cassandra
import cassandra.auth
import cassandra.cluster
import cassandra.policies
import tabulate

from . import cql
from . import exceptions
from . import migration as cstar_migration


CREATE_MIGRATIONS_TABLE = """
CREATE TABLE {keyspace}.{table} (
    id uuid,
    version int,
    name text,
    content text,
    checksum blob,
    state text,
    applied_at timestamp,
    PRIMARY KEY (id)
) WITH caching = {{'keys': 'NONE', 'rows_per_partition': 'NONE'}};
"""

CREATE_KEYSPACE = """
CREATE KEYSPACE {keyspace}
WITH REPLICATION = {replication}
AND DURABLE_WRITES = {durable_writes};
"""

DROP_KEYSPACE = """
DROP KEYSPACE IF EXISTS "{keyspace}";
"""

CREATE_DB_VERSION = """
INSERT INTO "{keyspace}"."{table}"
(id, version, name, content, checksum, state, applied_at)
VALUES (%s, %s, %s, %s, %s, %s, toTimestamp(now())) IF NOT EXISTS
"""

FINALIZE_DB_VERSION = """
UPDATE "{keyspace}"."{table}" SET state = %s WHERE id = %s IF state = %s
"""

DELETE_DB_VERSION = """
DELETE FROM "{keyspace}"."{table}" WHERE id = %s IF state = %s
"""


def cassandra_ddl_repr(data):
    """Generate a string representation of a map suitable for use in Cassandra DDL."""
    if isinstance(data, str):
        return "'" + re.sub(r"(?<!\\)'", "\\'", data) + "'"
    elif isinstance(data, dict):
        pairs = []
        for k, v in data.items():
            if not isinstance(k, str):
                raise ValueError('DDL map keys must be strings')

            pairs.append(cassandra_ddl_repr(k) + ': ' + cassandra_ddl_repr(v))
        return '{' + ', '.join(pairs) + '}'
    elif isinstance(data, int):
        return str(data)
    elif isinstance(data, bool):
        if data:
            return 'true'
        else:
            return 'false'
    else:
        raise ValueError('Cannot convert data to a DDL representation')


def confirmation_required(func):
    """Asks for the user's confirmation before calling the decorated function.

    This step is ignored when the script is not run from a TTY.
    """
    @functools.wraps(func)
    def wrapper(self, opts, *args, **kwargs):
        cli_mode = getattr(opts, 'cli_mode', False)
        if cli_mode and not opts.assume_yes:
            confirmation = input(f'The {func.__name__!r} operation cannot be undone. '
                                 'Are you sure? [y/N] ')
            if not confirmation.lower().startswith("y"):
                return
        opts.assume_yes = True
        return func(self, opts, *args, **kwargs)
    return wrapper


class Migrator(object):
    """Execute migration operations in a Cassandra database based on configuration.

    `opts` must contain at least the following attributes:
    - config_file: path to a YAML file containing the configuration
    - profiles: map of profile names to keyspace settings
    - user, password: authentication options. May be None to not use it.
    - hosts: comma-separated list of contact points
    - port: connection port
    """

    logger = logging.getLogger('Migrator')

    def __init__(self, config, profile='dev', hosts=['127.0.0.1'], port=9042,
                 user=None, password=None, protocol_version=4,
                 host_cert_path=None, client_key_path=None,
                 client_cert_path=None):
        self.config = config

        try:
            self.current_profile = self.config.profiles[profile]
        except KeyError:
            raise ValueError(f'Invalid profile name {profile!r}')

        if user:
            auth_provider = cassandra.auth.PlainTextAuthProvider(user, password)
        else:
            auth_provider = None

        if host_cert_path:
            ssl_options = self._build_ssl_options(
                host_cert_path,
                client_key_path,
                client_cert_path)
        else:
            ssl_options = None

        execution_profile = cassandra.cluster.ExecutionProfile(
            consistency_level=cassandra.ConsistencyLevel.ALL,
            load_balancing_policy=cassandra.policies.RoundRobinPolicy(),
            serial_consistency_level=cassandra.ConsistencyLevel.SERIAL,
            request_timeout=120,
        )
        execution_profiles = {
            cassandra.cluster.EXEC_PROFILE_DEFAULT: execution_profile,
        }

        self.cluster = cassandra.cluster.Cluster(
            contact_points=hosts,
            port=port,
            auth_provider=auth_provider,
            protocol_version=protocol_version,
            max_schema_agreement_wait=300,
            control_connection_timeout=10,
            connect_timeout=30,
            ssl_options=ssl_options,
            execution_profiles=execution_profiles,
        )

        self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._session is not None:
            self._session.shutdown()
            self._session = None

        if self.cluster is not None:
            self.cluster.shutdown()
            self.cluster = None

    def _build_ssl_options(self, host_cert_path, client_key_path,
                           client_cert_path):
        return {
            'ca_certs': host_cert_path,
            'certfile': client_cert_path,
            'keyfile': client_key_path
        }

    def _check_cluster(self):
        """Check if the cluster is still alive, raise otherwise"""
        if not self.cluster:
            raise RuntimeError("Cluster has shut down")

    def _init_session(self):
        if not self._session:
            self._session = self.cluster.connect()

    @property
    def session(self):
        """Initialize and configure a  Cassandra driver session if needed."""

        self._check_cluster()
        self._init_session()

        return self._session

    def _get_target_version(self, v):
        """Parses a version specifier to an actual numeric migration version.

        `v` might be:
        - None: the latest version is chosen
        - an int, or a numeric string: that exact version is chosen
        - a string: the version with that name is chosen if it exists

        If an invalid version is found, `ValueError` is raised.
        """

        if v is None:
            return len(self.config.migrations)

        if isinstance(v, int):
            num = v
        elif v.isdigit():
            num = int(v)
        else:
            try:
                num = self.config.migrations.index(v)
            except IndexError:
                num = -1

        if num <= 0:
            raise ValueError('Invalid database version, must be a number > 0 '
                             'or the name of an existing migration')
        return num

    def _q(self, query, **kwargs):
        """Format a query with the configured keyspace and migration table.

        `keyspace` and `table` are interpolated as named arguments.
        """
        return query.format(
            keyspace=self.config.keyspace, table=self.config.migrations_table,
            **kwargs)

    def _execute(self, query, *args, **kwargs):
        """Execute a query with the current session."""

        self.logger.debug(f'Executing query: {query}')
        return self.session.execute(query, *args, **kwargs)

    def _keyspace_exists(self):
        self._init_session()

        return self.config.keyspace in self.cluster.metadata.keyspaces

    def _ensure_keyspace(self):
        """Create the keyspace if it does not exist."""

        if self._keyspace_exists():
            return

        self.logger.info(f'Creating keyspace {self.config.keyspace!r}')

        profile = self.current_profile
        self._execute(self._q(
            CREATE_KEYSPACE,
            replication=cassandra_ddl_repr(profile['replication']),
            durable_writes=cassandra_ddl_repr(profile['durable_writes'])))

        self.cluster.refresh_keyspace_metadata(self.config.keyspace)

    def _table_exists(self):
        self._init_session()

        ks_metadata = self.cluster.metadata.keyspaces.get(self.config.keyspace,
                                                          None)
        # Fail if the keyspace is missing. If it should be created
        # automatically _ensure_keyspace() must be called first.
        if not ks_metadata:
            raise ValueError(f'Keyspace {self.config.keyspace!r} does not exist, '
                             'stopping')

        return self.config.migrations_table in ks_metadata.tables

    def _ensure_table(self):
        """Create the migration table if it does not exist."""

        if self._table_exists():
            return

        self.logger.info(
            f'Creating table {self.config.migrations_table!r} '
            f'in keyspace {self.config.keyspace!r}'
        )

        self._execute(self._q(CREATE_MIGRATIONS_TABLE))
        self.cluster.refresh_table_metadata(self.config.keyspace,
                                            self.config.migrations_table)

    def _verify_migrations(self, migrations, ignore_failed=False,
                           ignore_concurrent=False):
        """Verify if the version history persisted in Cassandra matches the migrations.

        Migrations with corresponding DB versions must have the same content and name.
        Every DB version must have a corresponding migration. Migrations without
        corresponding DB versions are considered pending, and returned as a result.

        Returns a list of tuples of (version, migration), with version starting
        from 1 and incrementing linearly.
        """

        # Load all the currently existing versions and sort them by version
        # number, as Cassandra can only sort it for us by partition
        cur_versions = self._execute(
            self._q('SELECT * FROM "{keyspace}"."{table}"'),
        )
        cur_versions = sorted(cur_versions, key=lambda v: v.version)

        last_version = None
        version_pairs = itertools.zip_longest(cur_versions, migrations)

        # Work through ordered pairs of (existing version, expected_migration), so that
        # stored versions and expected migrations can be compared for any differences
        for i, (version, migration) in enumerate(version_pairs, 1):
            # If version is empty, the migration has not yet been applied.
            # Keep track of the first such version, and append it to the
            # pending migrations list.
            if not version:
                break

            # If migration is empty, we have a version in the database with
            # no corresponding file. That might mean we're running the wrong
            # migration or have an out-of-date state, so we must fail
            if not migration:
                raise exceptions.UnknownMigration(version.version, version.name)

            # A migration was previously run and failed
            if version.state == cstar_migration.MigrationState.FAILED:
                if ignore_failed:
                    break

                raise exceptions.FailedMigration(version.version, version.name)

            last_version = version.version

            # A migration is in progress
            if version.state == cstar_migration.MigrationState.IN_PROGRESS:
                if ignore_concurrent:
                    break
                raise exceptions.ConcurrentMigration(version.version, version.name)

            # A stored version's migrations differs from the one in the FS
            if (
                    version.content != migration.content or
                    version.name != migration.name or
                    bytearray(version.checksum) != bytearray(migration.checksum)
            ):
                raise exceptions.InconsistentState(migration, version)

        if not last_version:
            pending_migrations = list(migrations)
        else:
            pending_migrations = list(migrations)[last_version:]

        if not pending_migrations:
            self.logger.info('Database is already up-to-date')
        else:
            self.logger.info(
                f'Pending migrations found. Current version: {last_version}, '
                f'Latest version: {len(migrations)}'
            )

        pending_migrations = enumerate(
            pending_migrations, (last_version or 0) + 1)
        return last_version, cur_versions, list(pending_migrations)

    def _create_version(self, version, migration):
        """Write an in-progress version entry to Cassandra.

        The migration is inserted with the given `version` number if and only
        if it does not exist already (using a CompareAndSet operation).

        If the insert suceeds (with the migration marked as in-progress), we
        can continue and actually execute it. Otherwise, there was a concurrent
        write and we must fail to allow the other write to continue.

        """

        self.logger.info(f'Writing in-progress migration version {version}: {migration}')

        version_id = uuid.uuid4()
        result = self._execute(
            self._q(CREATE_DB_VERSION),
            (
                version_id,
                version,
                migration.name,
                migration.content,
                bytearray(migration.checksum),
                cstar_migration.MigrationState.IN_PROGRESS,
            ),
        )

        if not result or not result.one().applied:
            raise exceptions.ConcurrentMigration(version, migration.name)

        return version_id

    def _apply_cql_migration(self, version, migration):
        """Persist and apply a CQL migration.

        First create an in-progress version entry, apply the script, then
        finalize the entry as succeeded, failed or skipped.
        """

        self.logger.info('Applying CQL migration')

        statements = cql.CQLSplitter.split(migration.content)

        try:
            if statements:
                self.logger.info(
                    f'Executing migration with {len(statements)} CQL statements'
                )

            for statement in statements:
                self.session.execute(statement)
        except Exception:
            self.logger.exception('Failed to execute migration')
            raise exceptions.FailedMigration(version, migration.name)

    def _apply_python_migration(self, version, migration):
        """Persist and apply a python migration.

        First create an in-progress version entry, apply the script, then
        finalize the entry as succeeded, failed or skipped.
        """
        self.logger.info('Applying python script')

        try:
            mod, _ = os.path.splitext(os.path.basename(migration.path))
            migration_script = importlib.import_module(mod)
            migration_script.execute(self._session)
        except Exception:
            self.logger.exception('Failed to execute script')
            raise exceptions.FailedMigration(version, migration.name)

    def _apply_migration(self, version, migration, skip=False):
        """Persist and apply a migration.

        When `skip` is True, do everything but actually run the script, for
        example, when baselining instead of migrating.
        """

        self.logger.info(f'Advancing to version {version}')

        version_uuid = self._create_version(version, migration)
        new_state = cstar_migration.MigrationState.FAILED
        sys.path.append(self.config.migrations_path)

        result = None

        try:
            if skip:
                self.logger.info('Migration is marked for skipping, '
                                 'not actually running script')
            else:
                if migration.is_python:
                    self._apply_python_migration(version, migration)
                else:
                    self._apply_cql_migration(version, migration)
        except Exception:
            self.logger.exception('Failed to execute migration')
            raise exceptions.FailedMigration(version, migration.name)
        else:
            new_state = (cstar_migration.MigrationState.SUCCEEDED if not skip
                         else cstar_migration.MigrationState.SKIPPED)
        finally:
            self.logger.info(f'Finalizing migration version with state {new_state!r}')
            result = self._execute(
                self._q(FINALIZE_DB_VERSION),
                (new_state, version_uuid, cstar_migration.MigrationState.IN_PROGRESS))

        if not result or not result.one().applied:
            raise exceptions.ConcurrentMigration(version, migration.name)

    def _cleanup_previous_versions(self, cur_versions):
        if not cur_versions:
            return

        last_version = cur_versions[-1]
        if last_version.state != cstar_migration.MigrationState.FAILED:
            return

        self.logger.warn(
            f'Cleaning up previous failed migration '
            f'(version {last_version.version}): {last_version.name}'
        )

        result = self._execute(
            self._q(DELETE_DB_VERSION),
            (last_version.id, cstar_migration.MigrationState.FAILED),
        )

        if not result.one().applied:
            raise exceptions.ConcurrentMigration(last_version.version,
                                                 last_version.name)

    def _advance(self, migrations, target, cur_versions, skip=False, force=False):
        """Apply all necessary migrations to reach a target version."""
        if force:
            self._cleanup_previous_versions(cur_versions)

        target_version = self._get_target_version(target)

        if migrations:
            # Set default keyspace so migrations don't need to refer to it manually
            self.session.execute(f'USE {self.config.keyspace};')

        for version, migration in migrations:
            if version > target_version:
                break

            self._apply_migration(version, migration, skip=skip)

        self.cluster.refresh_schema_metadata()

    @confirmation_required
    def migrate(self, opts):
        """Migrate a database to a given version, applying any needed migration."""

        self._check_cluster()

        self._ensure_keyspace()
        self._ensure_table()

        last_version, cur_versions, pending_migrations = \
            self._verify_migrations(self.config.migrations,
                                    ignore_failed=opts.force)

        self._advance(pending_migrations, opts.db_version, cur_versions,
                      force=opts.force)

    @confirmation_required
    def reset(self, opts):
        """Reset the database, by dropping an existing keyspace then running a migration.
        """
        self._check_cluster()

        self.logger.info(f'Dropping existing keyspace {self.config.keyspace!r}')

        self._execute(self._q(DROP_KEYSPACE))
        self.cluster.refresh_schema_metadata()

        opts.force = False
        self.migrate(opts)

    @confirmation_required
    def clear(self, opts):
        """Clear the database, by dropping an existing keyspace."""
        self._check_cluster()

        self.logger.info(f'Dropping existing keyspace {self.config.keyspace!r}')

        self._execute(self._q(DROP_KEYSPACE))
        self.cluster.refresh_schema_metadata()

    @confirmation_required
    def baseline(self, opts):
        """Baseline a database, by advancing migration state without changes."""

        self._check_cluster()
        self._ensure_table()

        last_version, cur_versions, pending_migrations = \
            self._verify_migrations(self.config.migrations,
                                    ignore_failed=False)

        self._advance(pending_migrations, opts.db_version, cur_versions,
                      skip=True)

    @staticmethod
    def _bytes_to_hex(bs):
        return codecs.getencoder('hex')(bs)[0]

    def status(self, opts):
        self._check_cluster()

        if not self._keyspace_exists():
            print(f'Keyspace {self.config.keyspace!r} does not exist')
            return

        if not self._table_exists():
            print(
                f'Migration table {self.config.migrations_table!r} does not exist in '
                f'keyspace {self.config.keyspace!r}'
            )
            return

        last_version, cur_versions, pending_migrations = self._verify_migrations(
            self.config.migrations, ignore_failed=True, ignore_concurrent=True)
        latest_version = len(self.config.migrations)

        print(tabulate.tabulate(
            (
                ('Keyspace:', self.config.keyspace),
                ('Migrations table:', self.config.migrations_table),
                ('Current DB version:', last_version),
                ('Latest DB version:', latest_version),
            ),
            tablefmt='plain'))

        if cur_versions:
            print('\n## Applied migrations\n')

            data = []
            for version in cur_versions:
                checksum = self._bytes_to_hex(version.checksum)
                date = arrow.get(version.applied_at).format()
                data.append(
                    (str(version.version), version.name, version.state, date, checksum),
                )
            print(tabulate.tabulate(data, headers=['#', 'Name', 'State',
                                                   'Date applied', 'Checksum']))

        if pending_migrations:
            print('\n## Pending migrations\n')

            data = []
            for version, migration in pending_migrations:
                checksum = self._bytes_to_hex(migration.checksum)
                data.append(
                    (str(version), migration.name, checksum),
                )
            print(tabulate.tabulate(data, headers=['#', 'Name', 'Checksum']))
