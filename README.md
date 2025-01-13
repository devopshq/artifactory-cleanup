# Artifactory cleanup #

`artifactory-cleanup` is an extended and flexible cleanup tool for JFrog Artifactory.

The tool has simple YAML-defined cleanup configuration and can be extended with your own rules on Python.
Everything must be as a code, even cleanup policies!

# Tables of Contents

<!-- toc -->

- [Artifactory cleanup](#artifactory-cleanup)
- [Tables of Contents](#tables-of-contents)
- [Installation](#installation)
- [Usage](#usage)
  - [Notes](#notes)
  - [Commands](#commands)
- [Rules](#rules)
  - [Common](#common)
  - [Delete](#delete)
  - [Keep](#keep)
  - [Docker](#docker)
  - [Filters](#filters)
  - [Create your own rule](#create-your-own-rule)
- [How to](#how-to)
  - [How to connect self-signed certificates for docker?](#how-to-connect-self-signed-certificates-for-docker)
  - [How to clean up Conan repository?](#how-to-clean-up-conan-repository)
  - [How to keep latest N docker images?](#how-to-keep-latest-n-docker-images)
- [Release](#release)

<!-- tocstop -->

# Installation

As simple as one command!

```bash
# docker
docker pull devopshq/artifactory-cleanup
docker run --rm devopshq/artifactory-cleanup artifactory-cleanup --help

# python (later we call it 'cli')
python3 -mpip install artifactory-cleanup
artifactory-cleanup --help
```

# Usage

Suppose you want to remove **all artifacts older than N days** from **reponame** repository.
You should take the following steps:

1. Install `artifactory-cleanup` (see above)
2. Create a configuration file `artifactory-cleanup.yaml`. variables.

```yaml
# artifactory-cleanup.yaml
artifactory-cleanup:
  server: https://repo.example.com/artifactory
  # $VAR is auto populated from environment variables
  user: $ARTIFACTORY_USERNAME
  password: $ARTIFACTORY_PASSWORD

  policies:
    - name: Remove all files from repo-name-here older than 7 days
      rules:
        - rule: Repo
          name: "reponame"
        - rule: DeleteOlderThan
          days: 7
```

3. Run the command **TO SHOW** (not remove) artifacts that will be deleted. By default `artifactory-cleanup` uses "dry
   mode".

```bash
# Set the credentials with delete permissions
export ARTIFACTORY_USERNAME=usernamehere
export ARTIFACTORY_PASSWORD=password

# docker
docker run --rm -v "$(pwd)":/app -e ARTIFACTORY_USERNAME -e ARTIFACTORY_PASSWORD devopshq/artifactory-cleanup artifactory-cleanup

# cli
artifactory-cleanup
```

4. Verify that right artifacts will be removed and add `--destroy` flag **TO REMOVE** artifacts:

```bash
# docker
docker run --rm -v "$(pwd)":/app -e ARTIFACTORY_USERNAME -e ARTIFACTORY_PASSWORD devopshq/artifactory-cleanup artifactory-cleanup --destroy

# cli
artifactory-cleanup --destroy
```

Looking for more examples? Check [examples](./examples) folder!

## Notes

- **Always** specify version of `artifactory-cleanup` when using it in the production. `1.0.0` is just an example, find the latest version in pypi: https://pypi.org/project/artifactory-cleanup/

```bash
# docker
docker pull devopshq/artifactory-cleanup:1.0.0
docker run --rm devopshq/artifactory-cleanup:1.0.0 artifactory-cleanup --version

# python (later we call it 'cli')
python3 -mpip install artifactory-cleanup==1.0.0
artifactory-cleanup --help
```

- Use CI servers or cron-like utilities to run `artifactory-cleanup` every day (or every hour). TeamCity and GitHub have
  built-in support and show additional logs format
- Do not save credentials in the configuration file, use environment variables.
- Use `--ignore-not-found` flag to ignore errors when the repository is not found. It's useful when you have a
  configuration for multiple repositories and some of them are not found.
- Use `--worker-count=<WORKER_NUM>` to increase the number of workers. By default, it's 1. It's useful when you have a lot of
  artifacts and you want to speed up the process.

## Commands ##

```bash
# Debug - "dry run" mode by default
# debug run - only print artifacts. it does not delete any artifacts
artifactory-cleanup

# Debug run only for policytestname.
artifactory-cleanup --policy-name policytestname

# REMOVE
# For remove artifacts use --destroy
artifactory-cleanup --destroy

# For remove artifacts use environment variable
export ARTIFACTORY_CLEANUP_DESTROY=True
artifactory-cleanup

# Specify config filename
artifactory-cleanup --config artifactory-cleanup.yaml

# Specify config filename using environment variable
export ARTIFACTORY_CLEANUP_CONFIG_FILE=artifactory-cleanup.yaml
artifactory-cleanup --config artifactory-cleanup.yaml

# Look in the future - shows what the tool WILL remove after 10 days
artifactory-cleanup --days-in-future=10

# Not satisfied with built-in rules? Write your own rules in python and connect them!
artifactory-cleanup --load-rules=myrule.py
docker run -v "$(pwd)":/app devopshq/artifactory-cleanup artifactory-cleanup --load-rules=myrule.py

# Save the table summary in a file
artifactory-cleanup --output=myfile.txt

# Save the summary in a json file
artifactory-cleanup --output=myfile.txt --output-format=json

# Save the summary in a json file and append the list of all removed artifacts
artifactory-cleanup --output=myfile.json --output-format json --output-artifacts
```

# Rules

## Common

- `Repo` - Apply the rule to one repository. If no name is specified, it is taken from the rule name (in `CleanupPolicy`
  definition)

```yaml
- rule: Repo
  name: reponame
```

```yaml
# OR - if you have a single policy for the repo - you can name the policy as reponame
# Both configurations are equal
policies:
  - name: reponame
    rules:
      - rule: Repo
```

- `RepoList` - Apply the policy to list of repositories.

```yaml
- rule: RepoList
  repos:
    - repo1
    - repo2
    - repo3
```

- `RepoByMask` - Apply rule to repositories matching by mask

```yaml
- rule: RepoByMask
  mask: "*.banned"
```

- `PropertyEq`- Delete repository artifacts only with a specific property value (property_key is the name of the
  parameter, property_value is the value)

```yaml
- rule: PropertyEq
  property_key: key-name
  property_value: 1
```

- `PropertyNeq`- Delete repository artifacts only if the value != specified. If there is no value, delete it anyway.
  Allows you to specify the deletion flag `do_not_delete = 1`

```yaml
- rule: PropertyNeq
  property_key: key-name
  property_value: 1
```

## Delete

- `DeleteOlderThan` - deletes artifacts that are older than N days

```yaml
- rule: DeleteOlderThan
  days: 1
```

- `DeleteWithoutDownloads`  - deletes artifacts that have never been downloaded (DownloadCount=0). Better to use
  with `DeleteOlderThan` rule

```yaml
- rule: DeleteWithoutDownloads
```

- `DeleteOlderThanNDaysWithoutDownloads` - deletes artifacts that are older than N days and have not been
  downloaded

```yaml
- rule: DeleteOlderThanNDaysWithoutDownloads
  days: 1
```

- `DeleteNotUsedSince` - delete artifacts that were downloaded, but for a long time. N days passed. Or not
  downloaded at all from the moment of creation and it's been N days

```yaml
- rule: DeleteNotUsedSince
  days: 1
```

- `DeleteEmptyFolders` - Clean up empty folders in given repository list

```yaml
- rule: DeleteEmptyFolders
```

- `DeleteByRegexpName` - delete artifacts whose name matches the specified regexp

```yaml
- rule: DeleteByRegexpName
  regex_pattern: "\d"
```

- `DeleteLeastRecentlyUsedFiles` - delete the least recently used files and keep at most requested number of files. Creation is interpreted as a first usage

```yaml
- rule: DeleteLeastRecentlyUsedFiles
  keep: 10
```

## Keep

- `KeepLatestNFiles` - Leaves the last (by creation time) files in the amount of N pieces. WITHOUT accounting
  subfolders

```yaml
- rule: KeepLatestNFiles
  count: 1
```

- `KeepLatestNFilesInFolder` - Leaves the last (by creation time) files in the number of N pieces in each
  folder

```yaml
- rule: KeepLatestNFilesInFolder
  count: 1
```

- `KeepLatestVersionNFilesInFolder` - Leaves the latest N (by version) files in each
  folder. The definition of the version is using regexp. By default it parses [semver](https://semver.org/) using the regex - `([\d]+\.[\d]+\.[\d]+)")`

```yaml
- rule: KeepLatestVersionNFilesInFolder
  count: 1
  custom_regexp: "[^\\d][\\._]((\\d+\\.)+\\d+)"
```

- `KeepLatestNupkgNVersions` - Leaves N nupkg (adds `*.nupkg` filter) in release feature builds

```yaml
- rule: KeepLatestNupkgNVersions
  count: 1
```

## Docker

- `DeleteDockerImagesOlderThan` - Delete docker images that are older than N days

```yaml
- rule: DeleteDockerImagesOlderThan
  days: 1
```

- `DeleteDockerImagesOlderThanNDaysWithoutDownloads` - Deletes docker images that are older than N days and have
  not been downloaded

```yaml
- rule: DeleteDockerImagesOlderThanNDaysWithoutDownloads
  days: 1
```

- `DeleteDockerImagesNotUsed` - Removes Docker image not downloaded since N days

```yaml
- rule: DeleteDockerImagesNotUsed
  days: 1
```

- `IncludeDockerImages` - Apply to docker images with the specified names and tags

```yaml
- rule: IncludeDockerImages
  masks: "*singlemask*"
- rule: IncludeDockerImages
  masks:
    - "*production*"
    - "*release*"
```

- `ExcludeDockerImages` - Exclude Docker images by name and tags.

```yaml
- rule: ExcludeDockerImages
  masks:
    - "*production*"
    - "*release*"
```

- `KeepLatestNVersionImagesByProperty(count=N, custom_regexp='some-regexp', number_of_digits_in_version=X)` - Leaves N
  Docker images with the same major. `(^\d+\.\d+\.\d+$)` is the default regexp how to determine version which matches semver `1.1.1`. If you
  need to add minor then set `number_of_digits_in_version` to 2 or if patch then set to 3 (by default we match major, which 1). Semver tags
  prefixed with `v` are supported by updating the regexp to include (an optional) `v` in the expression (e.g., `(^v?\d+\.\d+\.\d+$)`).

```yaml
- rule: KeepLatestNVersionImagesByProperty
  count: 1
  custom_regexp: "[^\\d][\\._]((\\d+\\.)+\\d+)"
```

- `KeepLatestNDockerImages(count=N)` - Leaves N
  most recently updated Docker image digests. This ensures all tags matching the same digest is kept.

```yaml
- rule: KeepLatestNDockerImages
  count: 1
```

- `DeleteDockerImageIfNotContainedInProperties(docker_repo='docker-local', properties_prefix='my-prop', image_prefix=None, full_docker_repo_name=None)`
  \- Remove Docker image, if it is not found in the properties of the artifact repository.

- `DeleteDockerImageIfNotContainedInPropertiesValue(docker_repo='docker-local', properties_prefix='my-prop', image_prefix=None, full_docker_repo_name=None)`
  \- Remove Docker image, if it is not found in the properties of the artifact repository.

## Filters

- `IncludePath` - Apply to artifacts by path / mask.

```yaml
- rule: IncludePath
  masks: "*production*"
- rule: IncludePath
  masks:
   - "*production*"
   - "*develop*"
```

- `IncludeFilename` - Apply to artifacts by name/mask

```yaml
- rule: IncludeFilename
  masks:
   - "*production*"
   - "*develop*"
```

- `ExcludePath` - Exclude artifacts by path/mask

```yaml
- rule: ExcludePath
  masks:
   - "*production*"
   - "*develop*"
```

- `ExcludeFilename` - Exclude artifacts by name/mask

```yaml
- rule: ExcludeFilename
  masks:
    - "*.tag.gz"
    - "*.zip"
```

## Create your own rule

If you want to create your own rule, you can do it!

The basic flow how the tool calls Rules:

1. `Rule.check(*args, **kwargs)` - verify that the Rule configured right. Call other services to get more information.
2. `Rule.aql_add_filter(filters)` - add Artifactory Query Language expressions
3. `Rule.aql_add_text(aql)` - add text to the result aql query
4. `artifactory-cleanup` calls Artifactory with AQL and pass the result to the next step
5. `Rule.filter(artifacts)` - filter out artifacts. The method returns **artifacts that will be removed!**.
    - To keep artifacts use `artifacts.keep(artifact)` method

Create `myrule.py` file at the same folder as `artifactory-cleanup.yaml`:

```python
# myrule.py
from typing import List

from artifactory_cleanup import register
from artifactory_cleanup.rules import Rule, ArtifactsList


class MySimpleRule(Rule):
    """
    This doc string is used as rule title

    For more methods look at Rule source code
    """

    def __init__(self, my_param: str, value: int):
        self.my_param = my_param
        self.value = value

    def aql_add_filter(self, filters: List) -> List:
        print(f"Today is {self.today}")
        print(self.my_param)
        print(self.value)
        return filters

    def filter(self, artifacts: ArtifactsList) -> ArtifactsList:
        """I'm here just to print the list"""
        print(self.my_param)
        print(self.value)
        # You can make requests to artifactory by using self.session:
        # url = f"/api/storage/{self.repo}"
        # r = self.session.get(url)
        # r.raise_for_status()
        return artifacts


# Register your rule in the system
register(MySimpleRule)
```

Use `rule: MySimpleRule` in configuration:

```yaml
# artifactory-cleanup.yaml
- rule: MySimpleRule
  my_param: "Hello, world!"
  value: 42
```

Specify `--load-rules` to the command:

```bash
# docker
docker run -v "$(pwd)":/app devopshq/artifactory-cleanup artifactory-cleanup --load-rules=myrule.py

# cli
artifactory-cleanup --load-rules=myrule.py
```

# How to

## How to connect self-signed certificates for docker?

In case you have set up your Artifactory self-signed certificates, place all certificates of the chain of trust into
the `certificates` folder and add additional argument to the command:

```bash
docker run -v "$(pwd)":/app -v "$(pwd)/certificates":/mnt/self-signed-certs/ devopshq/artifactory-cleanup artifactory-cleanup
```

## How to clean up Conan repository?

We can handle conan's metadata by creating two policies:

1. First one removes files but keep all metadata.
2. Second one look at folders and if it contains only medata files - removes it (because there's no associated with
   metadata files)

The idea came from https://github.com/devopshq/artifactory-cleanup/issues/47

```yaml
# artifactory-cleanup.yaml
artifactory-cleanup:
  server: https://repo.example.com/artifactory
  user: $ARTIFACTORY_USERNAME
  password: $ARTIFACTORY_PASSWORD

  policies:
    - name: Conan - delete files older than 60 days
      rules:
        - rule: Repo
          name: "conan-testing"
        - rule: DeleteNotUsedSince
          days: 60
        - rule: ExcludeFilename
          masks:
            - ".timestamp"
            - "index.json"
    - name: Conan - delete empty folders (to fix the index)
      rules:
        - rule: Repo
          name: "conan-testing"
        - rule: DeleteEmptyFolders
        - rule: ExcludeFilename
          masks:
            - ".timestamp"
            - "index.json"
```

## How to keep latest N docker images?

We can combine docker rules with usual "files" rules!

The idea came from https://github.com/devopshq/artifactory-cleanup/issues/61

```yaml
# artifactory-cleanup.yaml
artifactory-cleanup:
  server: https://repo.example.com/artifactory
  user: $ARTIFACTORY_USERNAME
  password: $ARTIFACTORY_PASSWORD

  policies:
    - name: Remove docker images, but keep last 3
      rules:
        # Select repo
        - rule: Repo
          name: docker-demo
        # Delete docker images older than 30 days
        - rule: DeleteDockerImagesOlderThan
          days: 30
        # Keep these tags for all images
        - rule: ExcludeDockerImages
          masks:
            - "*:latest"
            - "*:release*"
        # Exclude these docker tags
        - rule: ExcludePath
          masks: "*base-tools*"
        # Keep 3 docker tags for all images
        - rule: KeepLatestNFilesInFolder
          count: 3
```

# Release

In order to provide a new release of `artifactory-cleanup`, there are two steps involved.

1. Bump the version in the [setup.py](setup.py)
2. Bump the version in the [__init__.py](./artifactory_cleanup/__init__.py)
3. Create a Git release tag (in format `1.0.1`) by creating a release on GitHub
