# Available Rules

## common - rules that apply to all repositories

| Name | Description |
| --- | --- |
| `DeleteOlderThan(days=N)` | Deletes artifacts that are older than N days |
| `DeleteWithoutDownloads()` | Deletes artifacts that have never been downloaded (DownloadCount=0). Better to use with `DeleteOlderThan` rule |
| `DeleteOlderThanNDaysWithoutDownloads(days=N)` | Deletes artifacts that are older than N days and have not been downloaded |
| `DeleteNotUsedSince(days=N)` | Delete artifacts that were downloaded, but for a long time. N days passed. Or not downloaded at all from the moment of creation and it's been N days |
| `DeleteEmptyFolder()` | Clean up empty folders in given repository list |
| `KeepLatestNupkgNVersions(count=N)` | Leaves N nupkg (adds `*.nupkg` filter) in release feature builds |
| `KeepLatestNFiles(count=N)` | Leaves the last (by creation time) files in the amount of N pieces. WITHOUT accounting subfolders |
| `KeepLatestNFilesInFolder(count=N)` | Leaves the last (by creation time) files in the number of N pieces in each folder |
| `KeepLatestVersionNFilesInFolder(count, custom_regexp='some-regexp')` | Leaves the latest N (by version) files in each folder. The definition of the version is using regexp. By default `[^\d][\._]((\d+\.)+\d+)` |
| `Repo('reponame')` | Apply the rule to one repository. If no name is specified, it is taken from the rule name (in `CleanupPolicy` definition) |
| `RepoByMask('*.banned')` | Apply rule to repositories matching by mask |
| `PropertyEq(property_key, property_value)`| Delete repository artifacts only with a specific property value (property_name is the name of the parameter, property_value is the value) |
| `PropertyNeq(property_key, property_value)`| Delete repository artifacts only if the value != specified. If there is no value, delete it anyway. Allows you to specify the deletion flag `do_not_delete = 1`|

## docker - cleanup rules for docker images

| Name | Description |
| ---        | --- |
| `DeleteDockerImagesOlderThan(days=N)` | Delete docker images that are older than N days |
| `DeleteDockerImagesOlderThanNDaysWithoutDownloads(days=N)` | Deletes docker images that are older than N days and have not been downloaded |
| `DeleteDockerImagesNotUsed(days=N)` | Removes Docker image not downloaded since N days |
| `DeleteDockerImageIfNotContainedInProperties(docker_repo='docker-local', properties_prefix='my-prop', image_prefix=None, full_docker_repo_name=None)` | Remove Docker image, if it is not found in the properties of the artifact repository. |
| `DeleteDockerImageIfNotContainedInPropertiesValue(docker_repo='docker-local', properties_prefix='my-prop', image_prefix=None, full_docker_repo_name=None)` | Remove Docker image, if it is not found in the properties of the artifact repository. |
| `KeepLatestNVersionImagesByProperty(count=N, custom_regexp='some-regexp', number_of_digits_in_version=X)` | Leaves N Docker images with the same major. `(^ \d*\.\d*\.\d*.\d+$)` is the default regexp how to determine version. If you need to add minor then put 2 or if patch then put 3 (By default `1`) |


## filters - rules with different filters

| Name | Description | 
| --- | --- |
| `IncludePath('my-path/**')` | Apply to artifacts by path / mask. You can specify multiple paths: `IncludePath('*production*'), IncludePath(['*release*', '*master*'])` |
| `IncludeFilename('*.zip')` | Apply to artifacts by name/mask. You can specify multiple paths: `IncludeFilename('*-*'), IncludeFilename(['*tar.gz', '*.nupkg'])` |
| `IncludeDockerImages('*:latest*')` | Apply to docker images with the specified names and tags. You can specify multiple names and tags: `IncludeDockerImages('*:production*'), IncludeDockerImages(['ubuntu:*', 'debian:9'])` |
| `ExcludePath('my-path/**')` | Exclude artifacts by path/mask. You can specify multiple paths: `ExcludePath('*production*'), ExcludePath(['*release*', '*master*'])` |
| `ExcludeFilename('*.backup')` | Exclude artifacts by name/mask. You can specify multiple paths: `ExcludeFilename('*-*'), ExcludeFilename(['*tar.gz', '*.nupkg'])` |
| `ExcludeDockerImages('*:tag-*')` | Exclude Docker images by name and tags. You can specify multiple names and tags: `ExcludePath('*:production*'), ExcludePath(['ubuntu:*', 'debian:9'])` |
