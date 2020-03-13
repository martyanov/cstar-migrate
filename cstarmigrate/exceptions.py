class MigrationError(RuntimeError):
    """Base class for migration errors."""
    pass


class FailedMigration(MigrationError):
    """Database state contains failed migrations."""

    def __init__(self, version, name):
        self.version = version
        self.migration_name = name

        super(FailedMigration, self).__init__(
            f'Migration failed, cannot continue (version {version}): {name}')


class ConcurrentMigration(MigrationError):
    """Database state contains failed migrations."""

    def __init__(self, version, name):
        self.version = version
        self.migration_name = name

        super(ConcurrentMigration, self).__init__(
            f'Migration already in progress (version {version}): {name}')


class InconsistentState(MigrationError):
    """Database state differs from specified migrations."""

    def __init__(self, migration, version):
        self.migration = migration
        self.version = version

        super(InconsistentState, self).__init__(
            f'Found inconsistency between specified migration and stored '
            f'version: {migration} != {version}')


class UnknownMigration(MigrationError):
    """Database contains migrations that have not been specified."""
    def __init__(self, version, name):
        self.version = version
        self.migration_name = name

        super(UnknownMigration, self).__init__(
            f'Found version in database without corresponding '
            f'migration (version {version}): {name}')
