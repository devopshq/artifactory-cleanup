from datetime import date

from artifactory_cleanup import CleanupPolicy
from artifactory_cleanup.rules import (
    ArtifactsList,
    DeleteMavenArtifactsNotUsed,
    DeleteMavenArtifactsOlderThanNDays,
    DeleteMavenArtifactsOlderThanNDaysWithoutDownloads,
    ExcludeMavenSnapshots,
    IncludeMavenSnapshots,
    KeepLatestNMavenArtifacts,
    KeepLatestNVersionMavenArtifacts,
)
from tests.utils import makeas

TODAY = date(2021, 3, 31)


class TestDeleteMavenArtifactsOlderThanNDays:
    def test_aql_add_filter(self):
        rule = DeleteMavenArtifactsOlderThanNDays(days=7)
        rule.today = TODAY
        filters = rule.aql_add_filter([])
        assert filters == [{"created": {"$lt": "2021-03-24"}}]


class TestDeleteMavenArtifactsOlderThanNDaysWithoutDownloads:
    def test_aql_add_filter(self):
        rule = DeleteMavenArtifactsOlderThanNDaysWithoutDownloads(days=7)
        rule.today = TODAY
        filters = rule.aql_add_filter([])
        assert filters == [
            {
                "$and": [
                    {"stat.downloads": {"$eq": None}},
                    {"stat.remote_downloads": {"$eq": None}},
                    {"created": {"$lte": "2021-03-24"}},
                ]
            }
        ]


class TestDeleteMavenArtifactsNotUsed:
    def test_aql_add_filter(self):
        rule = DeleteMavenArtifactsNotUsed(days=7)
        rule.today = TODAY
        filters = rule.aql_add_filter([])
        last_day = "2021-03-24"
        assert filters == [
            {
                "$or": [
                    {
                        "$and": [
                            {"stat.downloaded": {"$lte": last_day}},
                            {"stat.remote_downloaded": {"$lte": last_day}},
                        ]
                    },
                    {
                        "$and": [
                            {"stat.downloaded": {"$lte": last_day}},
                            {"stat.remote_downloads": {"$eq": None}},
                        ]
                    },
                    {
                        "$and": [
                            {"stat.downloads": {"$eq": None}},
                            {"stat.remote_downloaded": {"$lte": last_day}},
                        ]
                    },
                    {
                        "$and": [
                            {"stat.downloads": {"$eq": None}},
                            {"stat.remote_downloads": {"$eq": None}},
                            {"created": {"$lte": last_day}},
                        ]
                    },
                ]
            }
        ]


class TestExcludeMavenSnapshots:
    def test_aql_add_filter(self):
        rule = ExcludeMavenSnapshots()
        filters = rule.aql_add_filter([])
        assert filters == [{"path": {"$nmatch": "*SNAPSHOT*"}}]


class TestIncludeMavenSnapshots:
    def test_aql_add_filter(self):
        rule = IncludeMavenSnapshots()
        filters = rule.aql_add_filter([])
        assert filters == [{"path": {"$match": "*SNAPSHOT*"}}]


class TestKeepLatestNMavenArtifacts:
    def test_filter(self):
        # Two coordinates (foo, bar). foo has 3 versions, bar has 2.
        # Each version has a jar + pom to prove "all files of a version" stay.
        data = [
            # org/acme/foo
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.pom",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.pom",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/3.0.0",
                "name": "foo-3.0.0.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
            # org/acme/bar
            {
                "repo": "some-repo",
                "path": "org/acme/bar/0.5.0",
                "name": "bar-0.5.0.jar",
                "created": "2021-01-15T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/bar/0.6.0",
                "name": "bar-0.6.0.jar",
                "created": "2021-02-15T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNMavenArtifacts(count=2))
        remove_these = policy.filter(artifacts)

        # foo: keep 3.0.0 + 2.0.0 -> remove both files of 1.0.0
        # bar: keep both versions -> remove nothing
        expected = [
            {"path": "org/acme/foo/1.0.0", "name": "foo-1.0.0.jar"},
            {"path": "org/acme/foo/1.0.0", "name": "foo-1.0.0.pom"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_version_dated_by_newest_file(self):
        # Two files for 1.0.0 have different created timestamps; the version
        # must be ranked by the newest one so ordering is correct.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.pom",
                "created": "2021-01-02T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-01-03T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        expected = [
            {"path": "org/acme/foo/1.0.0", "name": "foo-1.0.0.jar"},
            {"path": "org/acme/foo/1.0.0", "name": "foo-1.0.0.pom"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_count_larger_than_versions_keeps_everything(self):
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNMavenArtifacts(count=10))
        remove_these = policy.filter(artifacts)

        assert list(remove_these) == []

    def test_repo_isolation(self):
        # Same coordinates in two repos must be treated as separate groups.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "other-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "other-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        expected = [
            {"repo": "some-repo", "path": "org/acme/foo/1.0.0"},
            {"repo": "other-repo", "path": "org/acme/foo/1.0.0"},
        ]
        assert makeas(remove_these, expected) == expected


class TestKeepLatestNVersionMavenArtifacts:
    def test_filter_numeric_ordering(self):
        # Verifies numeric (not lexicographic) version comparison:
        # 0.1.200 must be newer than 0.1.99
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/0.1.99",
                "name": "foo-0.1.99.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/0.1.100",
                "name": "foo-0.1.100.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/0.1.200",
                "name": "foo-0.1.200.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNVersionMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        # keep 0.1.200 (highest), remove 0.1.99 and 0.1.100
        expected = [
            {"path": "org/acme/foo/0.1.99"},
            {"path": "org/acme/foo/0.1.100"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_filter_all_unparseable_keeps_everything(self):
        # When no version matches the regexp every artifact is kept (nothing deleted).
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0",
                "name": "foo-1.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0",
                "name": "foo-2.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNVersionMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        assert list(remove_these) == []

    def test_filter_unparseable_version_is_kept(self):
        # '1.0' has only two version segments and does not match the default
        # three-segment regexp, so it counts as unparseable and must be kept.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.1.0",
                "name": "foo-2.1.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0",
                "name": "foo-1.0.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNVersionMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        # '1.0' is kept (unparseable); of the parseable versions 2.1.0 is the
        # latest and is kept, so only 2.0.0 is removed.
        expected = [{"path": "org/acme/foo/2.0.0"}]
        assert makeas(remove_these, expected) == expected

    def test_filter_version_with_prefix(self):
        # Custom regexp capturing a numeric version behind a fixed prefix.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/uat-1.0.0",
                "name": "foo-uat-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/uat-1.0.99",
                "name": "foo-uat-1.0.99.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/uat-1.0.200",
                "name": "foo-uat-1.0.200.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy(
            "test",
            KeepLatestNVersionMavenArtifacts(
                count=1, custom_regexp=r"^uat-(\d+\.\d+\.\d+$)"
            ),
        )
        remove_these = policy.filter(artifacts)

        # uat-1.0.200 is the latest -> remove uat-1.0.0 and uat-1.0.99
        expected = [
            {"path": "org/acme/foo/uat-1.0.0"},
            {"path": "org/acme/foo/uat-1.0.99"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_count_larger_than_versions_keeps_everything(self):
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNVersionMavenArtifacts(count=10))
        remove_these = policy.filter(artifacts)

        assert list(remove_these) == []

    def test_multiple_artifact_groups(self):
        # foo and bar are independent groups; within each group count=1 per major.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.1.0",
                "name": "foo-1.1.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/bar/2.0.0",
                "name": "bar-2.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/bar/2.1.0",
                "name": "bar-2.1.0.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNVersionMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        expected = [
            {"path": "org/acme/foo/1.0.0"},
            {"path": "org/acme/bar/2.0.0"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_repo_isolation(self):
        # Same coordinates in two repos are independent groups.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.1.0",
                "name": "foo-1.1.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "other-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "other-repo",
                "path": "org/acme/foo/1.1.0",
                "name": "foo-1.1.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNVersionMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        expected = [
            {"repo": "some-repo", "path": "org/acme/foo/1.0.0"},
            {"repo": "other-repo", "path": "org/acme/foo/1.0.0"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_filter_number_of_digits_in_version_1_majors_are_independent(self):
        # Default number_of_digits_in_version=1: 1.x and 2.x are separate groups.
        # With count=1 the highest version of EACH major is kept, not just the
        # single global highest.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.1.0",
                "name": "foo-1.1.0.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.1.0",
                "name": "foo-2.1.0.jar",
                "created": "2021-04-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNVersionMavenArtifacts(count=1))
        remove_these = policy.filter(artifacts)

        # 1.1.0 is kept (highest 1.x) and 2.1.0 is kept (highest 2.x)
        expected = [
            {"path": "org/acme/foo/1.0.0"},
            {"path": "org/acme/foo/2.0.0"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_filter_number_of_digits_in_version_0_all_versions_in_one_group(self):
        # number_of_digits_in_version=0 puts all versions of an artifact into
        # one group regardless of major, so count=1 keeps only the single
        # highest version across all major and patch lines.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.1",
                "name": "foo-1.0.1.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.0",
                "name": "foo-2.0.0.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/2.0.1",
                "name": "foo-2.0.1.jar",
                "created": "2021-04-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy(
            "test", KeepLatestNVersionMavenArtifacts(count=1, number_of_digits_in_version=0)
        )
        remove_these = policy.filter(artifacts)

        # 2.0.1 is the highest across all versions; everything else is removed
        expected = [
            {"path": "org/acme/foo/1.0.0"},
            {"path": "org/acme/foo/1.0.1"},
            {"path": "org/acme/foo/2.0.0"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_filter_number_of_digits_in_version_2(self):
        # number_of_digits_in_version=2 keeps count versions per major.minor line.
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.0",
                "name": "foo-1.0.0.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.0.1",
                "name": "foo-1.0.1.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.1.0",
                "name": "foo-1.1.0.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/1.1.1",
                "name": "foo-1.1.1.jar",
                "created": "2021-04-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy(
            "test", KeepLatestNVersionMavenArtifacts(count=1, number_of_digits_in_version=2)
        )
        remove_these = policy.filter(artifacts)

        # 1.0.x group: keep 1.0.1, remove 1.0.0
        # 1.1.x group: keep 1.1.1, remove 1.1.0
        expected = [
            {"path": "org/acme/foo/1.0.0"},
            {"path": "org/acme/foo/1.1.0"},
        ]
        assert makeas(remove_these, expected) == expected

    def test_filter_custom_multigroup_version(self):
        # Custom regexp with multiple capturing groups, joined into one
        # numeric version (1-XXX-2-3 -> 1.2.3).
        data = [
            {
                "repo": "some-repo",
                "path": "org/acme/foo/uat-1-XXX-2-3",
                "name": "foo.jar",
                "created": "2021-01-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/uat-1-XXX-2-99",
                "name": "foo.jar",
                "created": "2021-02-01T00:00:00.000+02:00",
            },
            {
                "repo": "some-repo",
                "path": "org/acme/foo/uat-1-XXX-2-200",
                "name": "foo.jar",
                "created": "2021-03-01T00:00:00.000+02:00",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy(
            "test",
            KeepLatestNVersionMavenArtifacts(
                count=1, custom_regexp=r"^uat-(\d+)-XXX-(\d+)-(\d+)$"
            ),
        )
        remove_these = policy.filter(artifacts)

        # 1.2.200 is the latest -> remove 1.2.3 and 1.2.99
        expected = [
            {"path": "org/acme/foo/uat-1-XXX-2-3"},
            {"path": "org/acme/foo/uat-1-XXX-2-99"},
        ]
        assert makeas(remove_these, expected) == expected


class TestSnapshotRulesComposeInPolicy:
    def test_exclude_snapshots_builds_combined_aql(self):
        policy = CleanupPolicy(
            "test",
            DeleteMavenArtifactsOlderThanNDays(days=7),
            ExcludeMavenSnapshots(),
        )
        policy.init(session=None, today=TODAY)
        find_filters = policy._get_aql_find_filters()
        assert find_filters == {
            "$and": [
                {"created": {"$lt": "2021-03-24"}},
                {"path": {"$nmatch": "*SNAPSHOT*"}},
            ]
        }

    def test_include_snapshots_builds_combined_aql(self):
        policy = CleanupPolicy(
            "test",
            DeleteMavenArtifactsOlderThanNDays(days=7),
            IncludeMavenSnapshots(),
        )
        policy.init(session=None, today=TODAY)
        find_filters = policy._get_aql_find_filters()
        assert find_filters == {
            "$and": [
                {"created": {"$lt": "2021-03-24"}},
                {"path": {"$match": "*SNAPSHOT*"}},
            ]
        }
