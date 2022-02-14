# Artifactory cleanup #

`artifactory-cleanup` is a tool for cleaning artifacts in Jfrog Artifactory.

# Tables of Contents

<!-- toc -->

- [Installation](#installation)
- [Usage](#usage)
  * [Commands](#commands)
  * [Available Rules](#available-rules)
  * [Artifact cleanup policies](#artifactory-cleanup-policies)
  
<!-- tocstop -->

# Installation
Upgrade/install to the newest available version:
```bash
python3 -mpip install artifactory-cleanup

# Directly from git
python3 -mpip install git+https://github.com/devopshq/artifactory-cleanup.git

# To be able to change files
git clone https://github.com/devopshq/artifactory-cleanup.git
cd artifactory-cleanup
python3 -mpip install -e .
```

# Usage

Suppose you want to remove all artifacts older than N days from 'reponame'.
You should take the following steps:

1. Install `artifactory-cleanup`
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
3. Run the command to SHOW (not remove) artifacts that will be deleted:
```bash
artifactory-cleanup --user user --password password --artifactory-server https://repo.example.com/artifactory --config reponame.py
```
4. Add `--destroy` flag to REMOVE artifacts
```bash
artifactory-cleanup --destroy --user user --password password --artifactory-server https://repo.example.com/artifactory --config reponame.py
```

## Commands ##

```bash
# Debug
# debug run - only print founded artifacts. it do not delete
artifactory-cleanup --user user --password password --artifactory-server https://repo.example.com/artifactory --config reponame.py

# Clean up empty folder
# --remove-empty-folder
# You need to use the plugin https://github.com/jfrog/artifactory-user-plugins/tree/master/cleanup/deleteEmptyDirs to delete empty folders
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
