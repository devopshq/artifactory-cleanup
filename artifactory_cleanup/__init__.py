from artifactory_cleanup.cli import ArtifactoryCleanupCLI  # noqa
from artifactory_cleanup.loaders import registry
from artifactory_cleanup.rules.base import CleanupPolicy  # noqa


def register(rule):
    registry.register(rule)


__version__ = "1.0.14"
