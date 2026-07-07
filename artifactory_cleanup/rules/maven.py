import re
from collections import defaultdict

from artifactory_cleanup.rules.base import Rule
from artifactory_cleanup.rules.delete import (
    DeleteNotUsedSince,
    DeleteOlderThan,
    DeleteOlderThanNDaysWithoutDownloads,
)


class RuleForMaven(Rule):
    """
    Parent class for Maven rules.

    Maven lays artifacts out on a coordinate path::

        <repo>/<groupId>/<artifactId>/<version>/<artifactId>-<version>.<ext>

    e.g. ``org/acme/foo/1.0.0/foo-1.0.0.jar``.

    Artifacts are grouped by ``(repo, groupId/artifactId)``. The ``<version>``
    directory holds all files of a single release (jar, pom, sources,
    checksums, ...) and is treated as one unit.

    https://maven.apache.org/guides/mini/guide-naming-conventions.html
    """

    SNAPSHOT_MARKER = "SNAPSHOT"

    @staticmethod
    def _group_key(artifact):
        """(repo, groupId/artifactId) - the parent of the version folder."""
        path = artifact["path"]
        coordinates, _, _version = path.rpartition("/")
        return artifact["repo"], coordinates

    @staticmethod
    def _version_key(artifact):
        """The version directory = last path segment."""
        return artifact["path"].rsplit("/", 1)[-1]


class DeleteMavenArtifactsOlderThanNDays(DeleteOlderThan, RuleForMaven):
    """
    Delete Maven artifacts older than ``days`` days.
    """


class DeleteMavenArtifactsOlderThanNDaysWithoutDownloads(
    DeleteOlderThanNDaysWithoutDownloads, RuleForMaven
):
    """
    Delete Maven artifacts that are older than ``days`` days AND have never
    been downloaded.
    """


class DeleteMavenArtifactsNotUsed(DeleteNotUsedSince, RuleForMaven):
    """
    Delete Maven artifacts that have not been downloaded for ``days`` days,
    or were never downloaded and are at least ``days`` days old.
    """


class _FilterMavenSnapshots(RuleForMaven):
    """
    Base class for the SNAPSHOT include/exclude rules.

    Matches on the version *directory* (e.g. ``1.0.0-SNAPSHOT``), not the
    file name, because timestamped snapshot files drop the literal token
    while their parent directory always keeps it.
    """

    operator = None

    def __init__(self):
        if self.operator is None:
            raise AttributeError("Attribute 'operator' must be specified")

    def aql_add_filter(self, filters):
        filter_ = {
            "path": {
                self.operator: f"*{self.SNAPSHOT_MARKER}*",
            }
        }
        filters.append(filter_)
        return super().aql_add_filter(filters)


class ExcludeMavenSnapshots(_FilterMavenSnapshots):
    """
    Exclude Maven SNAPSHOT artifacts from cleanup (keep only releases in scope).
    """

    operator = "$nmatch"


class IncludeMavenSnapshots(_FilterMavenSnapshots):
    """
    Apply the policy only to Maven SNAPSHOT artifacts.
    """

    operator = "$match"


class KeepLatestNMavenArtifacts(RuleForMaven):
    """
    Keep the latest ``count`` versions of each Maven artifact, ordered by
    creation date.
    """

    def __init__(self, count: int):
        self.count = count

    def filter(self, artifacts):
        # Map group -> {version: newest 'created' seen for that version}
        versions_created = defaultdict(dict)
        for artifact in artifacts:
            group = self._group_key(artifact)
            version = self._version_key(artifact)
            created = artifact["created"]
            current = versions_created[group].get(version)
            # Keep the newest 'created' among the files of a version so the
            # ordering reflects when the version was published.
            if current is None or created > current:
                versions_created[group][version] = created

        # For each group decide which versions to keep
        versions_to_keep = {}
        for group, version_map in versions_created.items():
            ordered = sorted(
                version_map.items(), key=lambda kv: kv[1], reverse=True
            )
            keep = {version for version, _created in ordered[: self.count]}
            versions_to_keep[group] = keep

        # Mark artifacts to keep
        for artifact in artifacts[:]:
            group = self._group_key(artifact)
            version = self._version_key(artifact)
            if version in versions_to_keep.get(group, set()):
                artifacts.keep(artifact)

        return artifacts


class KeepLatestNVersionMavenArtifacts(RuleForMaven):
    r"""
    Keep the latest ``count`` versions of each Maven artifact, ordered by
    semantic version number rather than creation date.

    Artifacts are grouped by ``(repo, groupId/artifactId)`` and then by the
    first ``number_of_digits_in_version`` version segments. With the default
    of ``1``, ``count`` versions are kept per major version line (``1.x`` and
    ``2.x`` are treated independently).

    The version is parsed from the version directory using ``custom_regexp``
    (default ``([\d]+\.[\d]+\.[\d]+)`` — matches ``1.2.3``). Versions are
    compared numerically, so ``0.1.200`` is newer than ``0.1.99``. Artifacts
    whose version cannot be parsed are kept and excluded from the count.
    """

    def __init__(
        self,
        count: int,
        custom_regexp: str = r"([\d]+\.[\d]+\.[\d]+)",
        number_of_digits_in_version: int = 1,
    ):
        self.count = count
        self.custom_regexp = custom_regexp
        self.number_of_digits_in_version = number_of_digits_in_version

    def _parse_version(self, artifact):
        match = re.match(self.custom_regexp, self._version_key(artifact))
        if not match or not match.groups():
            return None
        version_str = ".".join(map(str, match.groups()))
        version_str = re.sub(r"\.+", ".", version_str).strip(".")
        return version_str or None

    def _make_group(self, artifact, version_str):
        """(repo, groupId/artifactId, version_prefix) — prefix length set by number_of_digits_in_version."""
        prefix = tuple(int(x) for x in version_str.split("."))[:self.number_of_digits_in_version]
        return self._group_key(artifact) + (prefix,)

    def filter(self, artifacts):
        # Collect all parseable versions per group. Unparseable artifacts are
        # not counted towards the total and will never be deleted.
        group_versions = defaultdict(set)

        for artifact in artifacts:
            version_str = self._parse_version(artifact)
            if version_str is None:
                print(
                    "Warning: Could not identify version for {}/{} - "
                    "artifact will be kept and is not counted towards the "
                    "total version count".format(artifact["path"], artifact["name"])
                )
                continue
            group = self._make_group(artifact, version_str)
            group_versions[group].add(version_str)

        # For each group decide which versions to keep
        versions_to_keep = {}
        for group, versions in group_versions.items():
            ordered = sorted(
                versions, key=lambda v: [int(x) for x in v.split(".")], reverse=True
            )
            versions_to_keep[group] = set(ordered[: self.count])

        # Mark artifacts to keep
        for artifact in artifacts[:]:
            version_str = self._parse_version(artifact)
            if version_str is None:
                artifacts.keep(artifact)
                continue
            group = self._make_group(artifact, version_str)
            if version_str in versions_to_keep.get(group, set()):
                artifacts.keep(artifact)

        return artifacts
