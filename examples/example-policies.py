from artifactory_cleanup import rules
from artifactory_cleanup.rules import CleanupPolicy

RULES = [
    CleanupPolicy(
        "Remove all files from *.tmp repositories older then 7 days",
        rules.RepoByMask("*.tmp"),
        rules.DeleteOlderThan(days=7),
    ),
    CleanupPolicy(
        "docker-tmp",
        rules.RepoByMask("docker*-tmp"),
        rules.DeleteDockerImagesOlderThan(days=1),
    ),
    CleanupPolicy(
        "reponame.snapshot",
        rules.DeleteOlderThan(days=7),
    ),
    CleanupPolicy(
        "Remove all docker tags of every image except the most recent",
        rules.Repo("my-docker-repo"),
        rules.ExcludeDockerImages(["*:latest", "*:pre", "*:pro"]),
        rules.KeepLatestNDockerTags(3),
    ),
]
