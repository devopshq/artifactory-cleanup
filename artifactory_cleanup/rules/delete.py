from datetime import timedelta
from collections import defaultdict, deque

from artifactory_cleanup.rules.base import Rule


class delete_older_than(Rule):
    """Deletes artifacts older than `` days`` days"""

    def __init__(self, *, days):
        self.days = timedelta(days=days)

    def _aql_add_filter(self, aql_query_list):
        older_than_date = self.today - self.days
        older_than_date_txt = older_than_date.isoformat()
        print("Delete artifacts older than {}".format(older_than_date_txt))
        update_dict = {
            "created": {
                "$lt": older_than_date_txt,
            }
        }
        aql_query_list.append(update_dict)
        return aql_query_list


class delete_without_downloads(Rule):
    """
    Deletes artifacts that have never been downloaded. (DownloadCount=0).
    Better to use with :class:`delete_older_than`
    """

    def _aql_add_filter(self, aql_query_list):
        update_dict = {"stat.downloads": {"$eq": None}}
        aql_query_list.append(update_dict)
        return aql_query_list


class delete_older_than_n_days_without_downloads(Rule):
    """
    Deletes artifacts that are older than n days and have not been downloaded.
    """

    def __init__(self, *, days):
        self.days = timedelta(days=days)

    def _aql_add_filter(self, aql_query_list):
        last_day = self.today - self.days
        update_dict = {
            "$and": [
                {"stat.downloads": {"$eq": None}},
                {"created": {"$lte": last_day.isoformat()}},
            ],
        }
        aql_query_list.append(update_dict)
        return aql_query_list


class delete_not_used_since(Rule):
    """
    Delete artifacts that were downloaded, but for a long time. N days passed.
    Or not downloaded at all from the moment of creation and it's been N days.
    """

    def __init__(self, days):
        self.days = timedelta(days=days)

    def _aql_add_filter(self, aql_query_list):
        last_day = self.today - self.days

        update_dict = {
            "$or": [
                {"stat.downloaded": {"$lte": str(last_day)}},  # Скачивались давно
                {
                    "$and": [
                        {"stat.downloads": {"$eq": None}},  # Не скачивались
                        {"created": {"$lte": str(last_day)}},
                    ]
                },
            ]
        }

        aql_query_list.append(update_dict)

        return aql_query_list


class delete_empty_folder(Rule):
    """
    Clean up empty folders in local repositories. A special rule that runs separately on all repositories.

    Refers to the plugin
    https://github.com/jfrog/artifactory-user-plugins/tree/master/cleanup/deleteEmptyDirs
    """

    def _aql_add_filter(self, aql_query_list):
        # Get list of all files and folders
        all_files_dict = {
            "path": {
                "$match": "**"
            },
            "type": {"$eq": "any"}
        }
        aql_query_list.append(all_files_dict)
        return aql_query_list

    def _filter_result(self, result_artifact):

        # convert list of files to dict
        # Source: https://stackoverflow.com/a/58917078

        def nested_dict():
            """
            Creates a default dictionary where each value is an other default dictionary.
            """
            return defaultdict(nested_dict)

        def default_to_regular(d):
            """
            Converts defaultdicts of defaultdicts to dict of dicts.
            """
            if isinstance(d, defaultdict):
                d = {k: default_to_regular(v) for k, v in d.items()}
            return d

        def get_path_dict(artifacts):
            new_path_dict = nested_dict()
            for artifact in artifacts:
                parts = artifact["path"].split('/')
                if parts:
                    marcher = new_path_dict
                    for key in parts:
                        # We need the repo for the root level folders. They are not in the
                        # artifacts list
                        marcher[key]['data'] = {
                            "repo": artifact['repo']
                        }
                        marcher = marcher[key]['children']
                    marcher[artifact["name"]]['data'] = artifact
            return default_to_regular(new_path_dict)

        artifact_tree = get_path_dict(result_artifact)

        # Now we have a dict with all folders and files
        # An empty folder is represented if it is a dict and does not have any keys

        def get_folder_artifacts_with_no_children(item, path=""):

            empty_folder_artifacts = deque()

            def _add_to_del_list(key):
                empty_folder_artifacts.append(item[key]['data'])
                # Also delete the item from the children list to recursively delete folders
                # upwards
                del item[key]


            for x in list(item.keys()):
                if 'type' in item[x]['data'] and item[x]['data']['type'] == "file":
                    continue
                if not 'path' in item[x]['data']:
                    # Set the path and name for root folders which were not explicitly in the
                    # artifacts list
                    item[x]['data']["path"] = path
                    item[x]['data']["name"] = x
                if not 'children' in item[x] or len(item[x]['children']) == 0:
                    # This an empty folder
                    _add_to_del_list(x)
                else:
                    artifacts = get_folder_artifacts_with_no_children(item[x]['children'],
                                                                      path=path + "/" + x if
                                                                      len(path) > 0 else x)
                    if len(item[x]['children']) == 0:
                        # just delete the whole folder since all children are empty
                        _add_to_del_list(x)
                    else:
                        empty_folder_artifacts.extend(artifacts)

            return empty_folder_artifacts

        return list(get_folder_artifacts_with_no_children(artifact_tree))
