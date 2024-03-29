import argparse
import logging
import os
import subprocess
import sys

from . import config as cstar_config
from . import exceptions
from . import migration as cstar_migration
from . import migrator as cstar_migrator


def open_file(filename):
    if sys.platform == 'win32':
        os.startfile(filename)
    else:
        if 'XDG_CURRENT_DESKTOP' in os.environ:
            opener = ['xdg-open']
        elif 'EDITOR' in os.environ:
            opener = [os.environ['EDITOR']]
        else:
            opener = ['vi']

        opener.append(filename)
        subprocess.call(opener)


def main(argv=None):
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('cassandra.policies').setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(description='Cassandra schema migration tool')
    parser.add_argument('-H', '--hosts', default='127.0.0.1',
                        help='Comma-separated list of contact points')
    parser.add_argument('-p', '--port', type=int, default=9042,
                        help='Connection port')
    parser.add_argument('-u', '--user',
                        help='Connection username')
    parser.add_argument('-P', '--password',
                        help='Connection password')
    parser.add_argument('-l', '--protocol-version', type=int, default=4,
                        help='Connection protocol version')
    parser.add_argument('-c', '--config-file', default='cstar-migrate.yml',
                        help='Path to configuration file')
    parser.add_argument('-m', '--profile', default='dev',
                        help='Name of keyspace profile to use')
    parser.add_argument('-s', '--ssl-cert', default=None,
                        help="""
                        File path of .pem or .crt containing certificate of the
                        cassandra host you are connecting to (or the
                        certificate of the CA that signed the host certificate).
                        If this option is provided, cstar-migrate will use
                        ssl to connect to the cluster. If this option is not
                        provided, the -k and -t options will be ignored. """)
    parser.add_argument('-k', '--ssl-client-private-key', default=None,
                        help="""
                        File path of the .key file containing the private key
                        of the host on which the cstar-migrate command is
                        run. This option must be used in conjuction with the
                        -t option. This option is ignored unless the -s
                        option is provided.""")
    parser.add_argument('-t', '--ssl-client-cert', default=None,
                        help="""
                        File path of the .crt file containing the public
                        certificate of the host on which the cstar-migrate
                        command is run. This certificate (or the CA that signed
                        it) must be trusted by the cassandra host that
                        migrations are run against. This option must be used in
                        conjuction with the -k option. This option is ignored
                        unless the -s option is provided.""")
    parser.add_argument('-y', '--assume-yes', action='store_true',
                        help='Automatically answer "yes" for all questions')

    commands = parser.add_subparsers(help='sub-command help')

    migrate = commands.add_parser(
        'migrate',
        help='Migrate database up to the most recent (or specified) version '
             'by applying any new migration scripts in sequence')
    migrate.add_argument('-f', '--force', action='store_true',
                         help='Force migration even if last attempt failed')
    migrate.set_defaults(action='migrate')

    reset = commands.add_parser(
        'reset',
        help='Reset the database, by dropping an existing keyspace, '
             'then running a migration')
    reset.set_defaults(action='reset')

    clear = commands.add_parser(
        'clear',
        help='Clear the database, by dropping an existing keyspace')
    clear.set_defaults(action='clear')

    baseline = commands.add_parser(
        'baseline',
        help='Baseline database state, advancing migration information without '
             'making changes')
    baseline.set_defaults(action='baseline')

    stats = commands.add_parser(
        'status',
        help='Print current state of keyspace')
    stats.set_defaults(action='status')

    generate = commands.add_parser(
        'generate',
        help='Generate a new migration file')
    generate.add_argument(
        'description',
        help='Brief description of the new migration')
    generate.add_argument(
        '--python',
        dest='migration_type',
        action='store_const',
        const='python',
        default='cql',
        help='Generates a Python script instead of CQL.')

    generate.set_defaults(action='generate')

    for subcommand in (migrate, reset, baseline):
        subcommand.add_argument('db_version', metavar='VERSION', nargs='?',
                                help='Database version to baseline/reset/migrate to')

    opts = parser.parse_args(argv)

    # Enable user confirmation if we're running the script from a TTY
    opts.cli_mode = sys.stdin.isatty()

    config = cstar_config.MigrationConfig.load(opts.config_file)

    # Print help by default if no action was provided
    if getattr(opts, 'action', None) is None:
        parser.print_help()

        sys.exit(0)

    # Provide ability to open generated migration when executed from a TTY
    if opts.action == 'generate':
        new_path = cstar_migration.Migration.generate(
            config=config,
            description=opts.description,
            output=opts.migration_type,
        )
        if sys.stdin.isatty():
            open_file(new_path)

        print(os.path.basename(new_path))

        sys.exit(0)

    # Handle the rest
    with cstar_migrator.Migrator(
        config=config,
        profile=opts.profile,
        hosts=opts.hosts.split(','),
        port=opts.port,
        user=opts.user,
        password=opts.password,
        protocol_version=opts.protocol_version,
        host_cert_path=opts.ssl_cert,
        client_key_path=opts.ssl_client_private_key,
        client_cert_path=opts.ssl_client_cert,
    ) as migrator:
        cmd_method = getattr(migrator, opts.action)
        if not callable(cmd_method):
            print('Error: invalid command', file=sys.stderr)
            sys.exit(1)

        try:
            cmd_method(opts)
        except exceptions.MigrationError as e:
            print(f'Error: {e!r}', file=sys.stderr)
            sys.exit(1)
