from artifactory_cleanup import rules
from artifactory_cleanup.rules import CleanupPolicy

RULES = [
    # ------ ALL REPOS --------
    CleanupPolicy(
        "Очистка всех *.tmp - репозиториев",
        rules.RepoByMask("*.tmp"),
        rules.DeleteOlderThan(days=7),
    ),
    CleanupPolicy(
        "docker-tmp",
        rules.RepoByMask("docker*-tmp"),
        rules.DeleteDockerImagesOlderThan(days=1),
    ),
    # ------ Concrete repo --------
    CleanupPolicy(
        "reponame.snapshot",
        rules.DeleteOlderThan(days=7),
    ),
]
