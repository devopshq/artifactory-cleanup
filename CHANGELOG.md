# Changelog

## 1.0.0
- Support YAML configuration! #54 🎉
- Introduce new and stable (from this point) API for Rules #33

### Backward incompatible changes in API
In order to simplify API for Rule and CleanupPolicy and support some feature we have to introduce backward incompatible changes.

Keep them in mind if you create your own Rules and going to update from `0.4.1` to `1.0.0`.

#### Rules
- Methods have been changed:
  - `_aql_add_filter(aql_query_list)` => `aql_add_filter(items_find_filters)`
  - `_aql_add_text(aql_text)` => `aql_add_text(aql)`
  - `_filter_result(result_artifact)` => `filter(artifacts)`


## 0.4.2
- Fix: Failed to run artifactory-cleanup-0.4.1 command #64

## 0.4.1

- Use `CamelCase` style of rules by default.
- Internal refactoring, add tests, remove unused code.

## 0.4.0

- Remove `--remove-empty-folder` option. Artifactory provides corresponding built-in functionality already
- Change the `delete_empty_folder` rule to not depend on an external plugin, but directly delete files from this script

## 0.3.4

* Previous versions do not yet have a changelog
