## Available Rules

### common - rules that apply to all repositories

| Name | Description | 
| ---        | ---			 |
| `delete_older_than_n_days(N)` | Deletes artifacts older than N days    |
| `without_downloads()` | Deletes only artifacts that have DownloadCount = 0 |
| `repo('reponame')` | The rule applies to a specific repository |
| `repo_by_mask('*.banned')` | Rule applies to mask repositories |
| `property_eq(property_key, property_value)`| Delete repository artifacts only with a specific property value (property_name is the name of the parameter, property_value is the value).|
| `property_neq(property_key, property_value)`| Delete repository artifacts only if the value != specified. If there is no value, delete it anyway. Allows you to specify the deletion flag `do_not_delete = 1`|

### docker - cleanup rules for docker images

| Name | Description | 
| ---        | ---			 |
| `delete_images_older_than_n_days(N)` | Removes docker image older than N days |

### filters - rules with different filters

| Name | Description | 
| ---        | ---			 |
| `filter_by_path_mask('my/path*')` | All rules apply only to artifacts with a given path pattern |
| `filter_without_path_mask('master*'), filter_without_path_mask(['release*', 'master*'])` | DOES NOT apply to artifacts containing the given patterns in the PATH (maybe list, str) |
| `filter_without_filename_mask('*.nupkg*')` | DOES NOT apply to artifacts containing the given data in the NAME (can be list, str) |
