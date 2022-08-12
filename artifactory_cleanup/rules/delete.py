from datetime import timedelta

from artifactory_cleanup.rules import utils
from artifactory_cleanup.rules.base import Rule


class DeleteOlderThan(Rule):
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


class DeleteWithoutDownloads(Rule):
    """
    Deletes artifacts that have never been downloaded. (DownloadCount=0).
    Better to use with :class:`DeleteOlderThan`
    """

    def _aql_add_filter(self, aql_query_list):
        update_dict = {"stat.downloads": {"$eq": None}}
        aql_query_list.append(update_dict)
        return aql_query_list


class DeleteOlderThanNDaysWithoutDownloads(Rule):
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


class DeleteNotUsedSince(Rule):
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
                {"stat.downloaded": {"$lte": str(last_day)}},
                {
                    "$and": [
                        {"stat.downloads": {"$eq": None}},
                        {"created": {"$lte": str(last_day)}},
                    ]
                },
            ]
        }

        aql_query_list.append(update_dict)

        return aql_query_list


class DeleteEmptyFolder(Rule):
    """
    Remove empty folders.

    If you just want to clean up empty folders - Artifactory must do it automatically.
    We use the rule to help with some specific cases - look at README.md "FAQ: How to clean up Conan repository"
    """

    def _aql_add_filter(self, aql_query_list):
        # Get list of all files and folders
        all_files_dict = {"path": {"$match": "**"}, "type": {"$eq": "any"}}
        aql_query_list.append(all_files_dict)
        return aql_query_list

    def _filter_result(self, result_artifacts):
        repositories = utils.build_repositories(result_artifacts)
        folders = utils.get_empty_folders(repositories)
        return folders


# under_score - old style of naming
# Keep it for backward compatibility
delete_older_than = DeleteOlderThan
delete_without_downloads = DeleteWithoutDownloads
delete_older_than_n_days_without_downloads = DeleteOlderThanNDaysWithoutDownloads
delete_not_used_since = DeleteNotUsedSince
delete_empty_folder = DeleteEmptyFolder
