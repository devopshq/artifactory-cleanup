import re
from collections import defaultdict
from itertools import groupby


from artifactory_cleanup.rules.base import Rule


class KeepLatestNupkgNVersions(Rule):
    r"""Leaves ``count`` nupkg (adds * .nupkg filter) in release \ feature builds"""

    def __init__(self, count: int):
        self.count = count

    def filter(self, artifacts):
        artifact_grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        # Groupby:
        # - Nuget package name
        #   - Nuget Feature
        #       - Nuget MajorMinor version
        for artifact in artifacts:
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

        artifacts = self.remove_founded_artifacts(artifact_grouped, artifacts)

        return artifacts

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
                    artifact_count = len(sorted_artifact)
                    good_artifact_count = artifact_count - self.count
                    if good_artifact_count < 0:
                        good_artifact_count = 0

                    artifact_grouped[package][feature][version] = sorted_artifact[
                        good_artifact_count:
                    ]
        return artifact_grouped

    def remove_founded_artifacts(self, artifact_grouped, artifacts):
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
                        artifacts.keep(artifact)
        return artifacts

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


class KeepLatestNFiles(Rule):
    """Leaves the last (by creation time) files in the amount of N pieces. WITHOUT accounting subfolders"""

    def __init__(self, count: int):
        self.count = count

    def filter(self, artifacts):
        artifacts.sort(key=lambda x: x["created"])
        artifact_count = len(artifacts)
        good_artifact_count = artifact_count - self.count
        if good_artifact_count < 0:
            good_artifact_count = 0

        good_artifacts = artifacts[good_artifact_count:]
        artifacts.keep(good_artifacts)
        return artifacts


class KeepLatestNFilesInFolder(Rule):
    """Leaves the last (by creation time) files in the number of ``count`` pieces in each folder"""

    def __init__(self, count: int):
        self.count = count

    def filter(self, artifacts):
        artifacts.sort(key=lambda x: x["created"])
        artifacts_by_path = defaultdict(list)

        for artifact in artifacts:
            path = artifact["path"]
            artifacts_by_path[path].append(artifact)

        for path, _artifacts in artifacts_by_path.items():
            artifact_count = len(_artifacts)
            good_artifact_count = artifact_count - self.count
            if good_artifact_count < 0:
                good_artifact_count = 0

            good_artifacts = _artifacts[good_artifact_count:]
            artifacts.keep(good_artifacts)

        return artifacts


class KeepLatestVersionNFilesInFolder(Rule):
    r"""Leaves the latest (by version) files in each folder.

    The definition of the version is using regexp. By default ``r'[^ \d][[\._]]()((\d+\.)+\d+)')``
    """

    def __init__(self, count, custom_regexp=r"([\d]+\.[\d]+\.[\d]+)"):
        self.count = count
        self.custom_regexp = custom_regexp

    def filter(self, artifacts):
        artifacts_by_path_and_name = defaultdict(list)

        for artifact in artifacts[:]:
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
                print(
                    "Warning: Could not identify version for {}/{}".format(
                        artifact["path"], artifact["name"]
                    )
                )
                artifacts.keep(artifact)

        for artifactory_with_version in artifacts_by_path_and_name.values():
            artifactory_with_version.sort(
                key=lambda x: [int(x) for x in x[0].split(".")]
            )

            artifact_count = len(artifactory_with_version)
            good_artifact_count = artifact_count - self.count
            if good_artifact_count < 0:
                good_artifact_count = 0

            # artifactory_with_version contains list of (Version, Artifact)  pairs
            # Get the artifacts from that for return to 'keep'
            good_sets = artifactory_with_version[good_artifact_count:]
            good_artifacts = [good[1] for good in good_sets]

            artifacts.keep(good_artifacts)

        return artifacts
