import re
from collections import defaultdict
from itertools import groupby

from artifactory_cleanup.rules.base import Rule


class keep_latest_nupkg_n_version(Rule):
    r"""Leaves ``count`` nupkg (adds * .nupkg filter) in release \ feature builds"""

    def __init__(self, count):
        self.count = count

    def _filter_result(self, result_artifact):
        artifact_grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        # Groupby:
        # - Nuget package name
        #   - Nuget Feature
        #       - Nuget MajorMinor version
        for artifact in result_artifact:
            if not artifact["name"].endswith(".nupkg"):
                continue

            nuget_id = artifact["properties"]["nuget.id"]
            nuget_version = artifact["properties"]["nuget.version"]

            major, minor, _ = nuget_version.split(".", maxsplit=2)
            nuget_major_minor = (major, minor)

            nuget_feature = re.findall(r"-(.*)", nuget_version)
            nuget_feature = nuget_feature[0] if nuget_feature else ""

            artifact_grouped[nuget_id][nuget_feature][nuget_major_minor].append(
                artifact
            )

        artifact_grouped = self.good_artifacts(artifact_grouped)

        result_artifact = self.remove_founded_artifacts(
            artifact_grouped, result_artifact
        )

        return result_artifact

    def good_artifacts(self, artifact_grouped):
        for package, features in artifact_grouped.items():
            for feature, versions in features.items():
                for version in versions:
                    _artifacts = artifact_grouped[package][feature][version]
                    artifacts_by_version = {
                        x["properties"]["nuget.version"]: x for x in _artifacts
                    }
                    sorted_artifact = sorted(
                        artifacts_by_version.items(), key=self.keyfunc
                    )
                    sorted_artifact = [x[1] for x in sorted_artifact]
                    # Определяем количетсво артефактов
                    artifact_count = len(sorted_artifact)
                    good_artifact_count = artifact_count - self.count
                    if good_artifact_count < 0:
                        good_artifact_count = 0

                    artifact_grouped[package][feature][version] = sorted_artifact[
                        good_artifact_count:
                    ]
        return artifact_grouped

    def remove_founded_artifacts(self, artifact_grouped, result_artifact):
        # Remove found artifact
        for package, features in artifact_grouped.items():
            for feature, versions in features.items():
                for version, _artifacts in versions.items():
                    for artifact in _artifacts:
                        nuget_id = artifact["properties"]["nuget.id"]
                        nuget_version = artifact["properties"]["nuget.version"]
                        print(
                            "Filter package {nuget_id}.{nuget_version}".format(
                                **locals()
                            )
                        )
                        result_artifact.remove(artifact)
        return result_artifact

    @staticmethod
    def keyfunc(s):
        """
        Sorts collection by numbers
        Copy-paste from http://stackoverflow.com/a/16956262
        """
        s = s[0]
        return [
            int("".join(g)) if k else "".join(g)
            for k, g in groupby("\0" + s, str.isdigit)
        ]


class keep_latest_n_file(Rule):
    """ "Leaves the last (by creation time) files in the amount of N pieces. WITHOUT accounting subfolders"""

    def __init__(self, count):
        self.count = count

    def _aql_add_text(self, aql_text):
        aql_text = "{}.sort({})".format(aql_text, r'{"$asc" : ["created"]}')
        return aql_text

    def _filter_result(self, result_artifact):
        artifact_count = len(result_artifact)
        good_artifact_count = artifact_count - self.count
        if good_artifact_count < 0:
            good_artifact_count = 0

        good_artifacts = result_artifact[good_artifact_count:]
        for artifact in good_artifacts:
            print("Filter package {path}/{name}".format(**artifact))
            result_artifact.remove(artifact)

        return result_artifact


class keep_latest_n_file_in_folder(Rule):
    """Leaves the last (by creation time) files in the number of ``count`` pieces in each folder"""

    def __init__(self, count):
        self.count = count

    def _aql_add_text(self, aql_text):
        aql_text = "{}.sort({})".format(aql_text, r'{"$asc" : ["created"]}')
        return aql_text

    def _filter_result(self, result_artifact):
        artifacts_by_path = defaultdict(list)

        for artifact in result_artifact:
            path = artifact["path"]
            artifacts_by_path[path].append(artifact)

        for path, _artifacts in artifacts_by_path.items():
            artifact_count = len(_artifacts)
            good_artifact_count = artifact_count - self.count
            if good_artifact_count < 0:
                good_artifact_count = 0

            good_artifacts = _artifacts[good_artifact_count:]
            for artifact in good_artifacts:
                print("Filter package {path}/{name}".format(**artifact))
                result_artifact.remove(artifact)

        return result_artifact


class keep_latest_version_n_file_in_folder(Rule):
    r"""Leaves the latest (by version) files in each folder.

    The definition of the version is using regexp. By default ``r'[^ \d][[\._]]()((\d+\.)+\d+)')``
    """

    def __init__(self, count, custom_regexp=r"[^\d][\._]((\d+\.)+\d+)"):
        self.count = count
        self.custom_regexp = custom_regexp

    def _filter_result(self, result_artifact):
        artifacts_by_path_and_name = defaultdict(list)

        for artifact in result_artifact[:]:
            path = artifact["path"]
            version = re.findall(self.custom_regexp, artifact["name"])
            # save the version only if it was possible to uniquely determine it
            if len(version) == 1:
                version_str = (
                    version[0][0] if isinstance(version[0], tuple) else version[0]
                )
                artifactory_with_version = [version_str, artifact]
                name_without_version = artifact["name"][
                    : artifact["name"].find(version_str)
                ]
                key = path + "/" + name_without_version
                artifacts_by_path_and_name[key].append(artifactory_with_version)
            else:
                self.remove_artifact(artifact, result_artifact)

        for artifactory_with_version in artifacts_by_path_and_name.values():
            artifactory_with_version.sort(
                key=lambda x: [int(x) for x in x[0].split(".")]
            )

            artifact_count = len(artifactory_with_version)
            good_artifact_count = artifact_count - self.count
            if good_artifact_count < 0:
                good_artifact_count = 0

            good_artifacts = artifactory_with_version[good_artifact_count:]
            for artifact in good_artifacts:
                self.remove_artifact(artifact[1], result_artifact)

        return result_artifact
