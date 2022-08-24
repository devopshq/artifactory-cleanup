from artifactory_cleanup import CleanupPolicy, rules

RULES = [
    CleanupPolicy(
        "Remove all files from repo-name-here older then 7 days",
        rules.Repo("repo-name-here"),
        rules.DeleteOlderThan(days=7),
    ),
]
