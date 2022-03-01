# Available Rules

## common - rules that apply to all repositories

| Name | Description |
| --- | --- |
| `delete_older_than(days=N)` | Deletes artifacts that are older than N days |
| `delete_without_downloads()` | Deletes artifacts that have never been downloaded (DownloadCount=0). Better to use with `delete_older_than` rule |
| `delete_older_than_n_days_without_downloads(days=N)` | Deletes artifacts that are older than N days and have not been downloaded |
| `delete_not_used_since(days=N)` | Delete artifacts that were downloaded, but for a long time. N days passed. Or not downloaded at all from the moment of creation and it's been N days |
| `delete_empty_folder()` | Clean up empty folders in local repositories. A special rule that runs separately on all repositories. Refers to [deleteEmptyDirs](https://github.com/jfrog/artifactory-user-plugins/tree/master/cleanup/deleteEmptyDirs) plugin |
| `keep_latest_nupkg_n_version(count=N)` | Leaves N nupkg (adds `*.nupkg` filter) in release feature builds |
| `keep_latest_n_file(count=N)` | Leaves the last (by creation time) files in the amount of N pieces. WITHOUT accounting subfolders |
| `keep_latest_n_file_in_folder(count=N)` | Leaves the last (by creation time) files in the number of N pieces in each folder |
| `keep_latest_version_n_file_in_folder(count, custom_regexp='some-regexp')` | Leaves the latest N (by version) files in each folder. The definition of the version is using regexp. By default `[^\d][\._]((\d+\.)+\d+)` |
| `repo('reponame')` | Apply the rule to one repository. If no name is specified, it is taken from the rule name (in `CleanupPolicy` definition) |
| `repo_by_mask('*.banned')` | Apply rule to repositories matching by mask |
| `property_eq(property_key, property_value)`| Delete repository artifacts only with a specific property value (property_name is the name of the parameter, property_value is the value) |
| `property_neq(property_key, property_value)`| Delete repository artifacts only if the value != specified. If there is no value, delete it anyway. Allows you to specify the deletion flag `do_not_delete = 1`|

## docker - cleanup rules for docker images

| Name | Description |
| ---        | --- |
| `delete_docker_images_older_than(days=N)` | Delete docker images that are older than N days |
| `delete_docker_images_older_than_n_days_without_downloads(days=N)` | Deletes docker images that are older than N days and have not been downloaded |
| `delete_docker_images_not_used(days=N)` | Removes Docker image not downloaded since N days |
| `delete_docker_image_if_not_contained_in_properties(docker_repo='docker-local', properties_prefix='my-prop', image_prefix=None, full_docker_repo_name=None)` | Remove Docker image, if it is not found in the properties of the artifact repository. Warning: [Multiscanner project specific rule](https://wiki.ptsecurity.com/x/koFIAg) |
| `delete_docker_image_if_not_contained_in_properties_value(docker_repo='docker-local', properties_prefix='my-prop', image_prefix=None, full_docker_repo_name=None)` | Remove Docker image, if it is not found in the properties of the artifact repository. Warning: [Multiscanner project specific rule](https://wiki.ptsecurity.com/x/koFIAg) |
| `keep_latest_n_version_images_by_property(count=N, custom_regexp='some-regexp', number_of_digits_in_version=X)` | Leaves N Docker images with the same major. `(^ \d*\.\d*\.\d*.\d+$)` is the default regexp how to determine version. If you need to add minor then put 2 or if patch then put 3 (By default `1`) |


## filters - rules with different filters

| Name | Description | 
| --- | --- |
| `include_path('my-path/**')` | Apply to artifacts by path / mask. You can specify multiple paths: `include_path('*production*'), include_path(['*release*', '*master*'])` |
| `include_filename('*.zip')` | Apply to artifacts by name/mask. You can specify multiple paths: `include_filename('*-*'), include_filename(['*tar.gz', '*.nupkg'])` |
| `include_docker_images('*:latest*')` | Apply to docker images with the specified names and tags. You can specify multiple names and tags: `include_docker_images('*:production*'), include_docker_images(['ubuntu:*', 'debian:9'])` |
| `exclude_path('my-path/**')` | Exclude artifacts by path/mask. You can specify multiple paths: `exclude_path('*production*'), exclude_path(['*release*', '*master*'])` |
| `exclude_filename('*.backup')` | Exclude artifacts by name/mask. You can specify multiple paths: `exclude_filename('*-*'), exclude_filename(['*tar.gz', '*.nupkg'])` |
| `exclude_docker_images('*:tag-*')` | Exclude Docker images by name and tags. You can specify multiple names and tags: `exclude_path('*:production*'), exclude_path(['ubuntu:*', 'debian:9'])` |
