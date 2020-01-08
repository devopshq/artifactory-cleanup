# Artifactory cleanup #

`artifactory-cleanup` is a tool for cleaning artifacts in Jfrog Artifactory.

# Tables of Contents

<!-- toc -->

- [Install](#install)
- [Usage](#usage)
  * [Commands](#commands)
  * [Available Rules](#available-rules)
  * [Artifact cleanup policies](#artifactory-cleanup-policies)
  
<!-- tocstop -->

# Install #
Upgrade/install to the newest available version:
```bash
python3 -mpip install artifactory-cleanup --upgrade
```
Or specify version, e.g.:
```bash
python3 -mpip install artifactory-cleanup==0.1
```

# Usage

Suppose you want to remove all artifacts older than N days from 'reponame'.
You should take the following steps:

1. Install `artifactory-cleanup`
```bash
python3 -mpip install artifactory-cleanup
```
2. Сreate a python file, for example, `reponame.py` with the following contents:
```python
from artifactory_cleanup import rules
from artifactory_cleanup.rules import CleanupPolicy

RULES = [

    # ------ ALL REPOS --------
    CleanupPolicy(
       'Delete files older than 30 days',
        rules.repo('reponame'),
        rules.delete_older_than(days=30),
    ),
]
```
3. Run the command to remove artifacts:
```bash
artifactory-cleanup --destroy --user user --password password --artifactory-server https://repo.example.com/artifactory --config reponame.py
```
More advanced examples and rules see below.

## Commands ##

```bash
# Debug
# debug run - only print founded artifacts. it do not delete
artifactory-cleanup --user user --password password --artifactory-server https://repo.example.com/artifactory --config reponame.py

# Clean up empty folder
# --remove-empty-folder
artifactory-cleanup --remove-empty-folder --user user --password password --artifactory-server https://repo.example.com/artifactory

# Debug run only for ruletestname. Find any *ruletestname*
# debug run - only print founded artifacts. it do not delete
artifactory-cleanup --rule-name ruletestname --user user --password password --artifactory-server https://repo.example.com/artifactory --config reponame.py

# REMOVE
# For remove artifacts use --destroy
artifactory-cleanup --destroy --user user --password password --artifactory-server https://repo.example.com/artifactory  --config reponame.py
```

## Available Rules ##

All rules are imported from the `rules` module.
See also [List of available cleaning rules](docs/RULES)

## Artifact cleanup policies ##

To add a cleaning policy you need:

- Create a python file, for example, `reponame.py`. `artifacroty-cleanup` imports the variable `RULES`, so you can make a python package.
- Add a cleanup rule from the [available cleanup rules](docs/RULES).

Example

```python
from artifactory_cleanup import rules
from artifactory_cleanup.rules import CleanupPolicy

RULES = [

    CleanupPolicy(
       'Delete all * .tmp repositories older than 7 days',
        rules.repo_by_mask('*. tmp'),
        rules.delete_older_than(days = 7),
    ),
    CleanupPolicy(
        'Delete all images older than 30 days from docker-registry exclude latest, release',
        rules.repo('docker-registry'),
        rules.exclude_docker_images(['*:latest', '*:release*']),
        rules.delete_docker_images_not_used(days=30),
    ),
]
```
