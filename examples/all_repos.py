from artifactory_cleanup import rules
from artifactory_cleanup.rules import CleanupPolicy

RULES = [
    # ------ ALL REPOS --------
    CleanupPolicy(
        "Очистка всех *.tmp - репозиториев",
        rules.repo_by_mask("*.tmp"),
        rules.delete_older_than(days=7),
    ),
    CleanupPolicy(
        "docker-tmp",
        rules.repo_by_mask("docker*-tmp"),
        rules.delete_docker_images_older_than(days=1),
    ),
    # ------ Concrete repo --------
    CleanupPolicy(
        "reponame.snapshot",
        rules.delete_older_than(days=7),
    ),
]
