from datetime import timedelta
from collections import defaultdict, deque

from artifactory_cleanup.rules.base import Rule
from artifactory_cleanup.rules.utils import artifacts_list_to_tree, \
    folder_artifacts_without_children


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
        all_files_dict = {"path": {"$match": "**"}, "type": {"$eq": "any"}}
        aql_query_list.append(all_files_dict)
        return aql_query_list

    def _filter_result(self, result_artifact):

        artifact_tree = artifacts_list_to_tree(result_artifact)

        # Now we have a dict with all folders and files
        # An empty folder is represented by not having any children
        return list(folder_artifacts_without_children(artifact_tree))
