"""
Previous version of artifactory-cleanup worked with only py files.
Now the main settings is YAML file,
but you still can use the python-defined policies if you have complex logic
"""

from artifactory_cleanup import rules
from artifactory_cleanup.rules import CleanupPolicy

# The tool will be looking for RULES variables in the module
RULES = [
    CleanupPolicy(
        "Remove all files from repo-name-here older then 7 days",
        rules.Repo("repo-name-here"),
        rules.DeleteOlderThan(days=7),
    ),
]
