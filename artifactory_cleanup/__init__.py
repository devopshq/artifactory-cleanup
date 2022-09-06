from artifactory_cleanup.cli import ArtifactoryCleanupCLI  # noqa
from artifactory_cleanup.loaders import YamlConfigLoader
from artifactory_cleanup.rules.base import CleanupPolicy  # noqa


def register(rule):
    YamlConfigLoader.register(rule)
