class ArtifactoryCleanupException(Exception):
    pass


class InvalidConfigError(ArtifactoryCleanupException):
    pass


class NotificationError(ArtifactoryCleanupException):
    pass
