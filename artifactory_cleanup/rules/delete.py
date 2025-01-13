from datetime import timedelta
import re

from artifactory_cleanup.rules import utils
from artifactory_cleanup.rules.base import ArtifactsList, Rule


class DeleteOlderThan(Rule):
    """Deletes artifacts older than `` days`` days"""

    def __init__(self, *, days: int):
        self.days = timedelta(days=days)

    def aql_add_filter(self, filters):
        older_than_date = self.today - self.days
        older_than_date_txt = older_than_date.isoformat()
        print("Delete artifacts older than {}".format(older_than_date_txt))
        filter_ = {
            "created": {
                "$lt": older_than_date_txt,
            }
        }
        filters.append(filter_)
        return filters


class DeleteWithoutDownloads(Rule):
    """
    Deletes artifacts that have never been downloaded. (DownloadCount=0).
    Better to use with :class:`DeleteOlderThan`
    """

    def aql_add_filter(self, filters):
        filter_ = {
            "$and": [
                {"stat.downloads": {"$eq": None}},
                {"stat.remote_downloads":{"$eq": None}},
            ],
        }
        filters.append(filter_)
        return filters


class DeleteOlderThanNDaysWithoutDownloads(Rule):
    """
    Deletes artifacts that are older than n days and have not been downloaded.
    """

    def __init__(self, *, days: int):
        self.days = timedelta(days=days)

    def aql_add_filter(self, filters):
        last_day = self.today - self.days
        filter_ = {
            "$and": [
                {"stat.downloads": {"$eq": None}},
                {"stat.remote_downloads":{"$eq": None}},
                {"created": {"$lte": last_day.isoformat()}},
            ],
        }
        filters.append(filter_)
        return filters


class DeleteNotUsedSince(Rule):
    """
    Delete artifacts that were downloaded, but for a long time. N days passed.
    Or not downloaded at all from the moment of creation and it's been N days.
    """

    def __init__(self, days: int):
        self.days = timedelta(days=days)

    def aql_add_filter(self, filters):
        last_day = self.today - self.days

        filter_ = {
            "$or": [
                {
                    "$and": [
                        {"stat.downloaded": {"$lte": str(last_day)}},
                        {"stat.remote_downloaded": {"$lte": str(last_day)}},
                    ]
                },
                {
                    "$and": [
                        {"stat.downloaded": {"$lte": str(last_day)}},
                        {"stat.remote_downloads": {"$eq": None}},
                    ]
                },
                {
                    "$and": [
                        {"stat.downloads": {"$eq": None}},
                        {"stat.remote_downloaded": {"$lte": str(last_day)}},
                    ]
                },
                {
                    "$and": [
                        {"stat.downloads": {"$eq": None}},
                        {"stat.remote_downloads": {"$eq": None}},
                        {"created": {"$lte": str(last_day)}},
                    ]
                },
            ]
        }

        filters.append(filter_)

        return filters


class DeleteEmptyFolders(Rule):
    """
    Remove empty folders.

    If you just want to clean up empty folders - Artifactory must do it automatically.
    We use the rule to help with some specific cases - look at README.md "FAQ: How to clean up Conan repository"
    """

    def aql_add_filter(self, filters):
        # Get list of all files and folders
        all_files_dict = {"path": {"$match": "**"}, "type": {"$eq": "any"}}
        filters.append(all_files_dict)
        return filters

    def filter(self, artifacts):
        repositories = utils.build_repositories(artifacts)
        folders = utils.get_empty_folders(repositories)
        return folders


class DeleteByRegexpName(Rule):
    """
    Remove artifacts by regex pattern.
    """

    def __init__(self, regex_pattern):
        self.regex_pattern = rf"{regex_pattern}"

    def filter(self, artifacts: ArtifactsList) -> ArtifactsList:
        for artifact in artifacts[:]:
            if re.match(self.regex_pattern, artifact["name"]) is None:
                artifacts.remove(artifact)
        return artifacts


class DeleteLeastRecentlyUsedFiles(Rule):
    """
    Delete the least recently used files, and keep at most ``keep`` files.
    Creation is interpreted as a first usage.
    """

    def __init__(self, keep: int):
        self.keep = keep

    def filter(self, artifacts: ArtifactsList) -> ArtifactsList:
        # List will contain fresh files at the beginning
        artifacts.sort(key=utils.sort_by_usage, reverse=True)
        kept_artifacts = artifacts[:self.keep]
        artifacts.keep(kept_artifacts)
        return artifacts
