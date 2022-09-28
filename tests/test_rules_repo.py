from artifactory_cleanup.rules import RepoList


def test_RepoList():
    rule = RepoList(repos=["repo1", "repo2", "repo3"])
    filters = []
    rule.aql_add_filter(filters)
    assert filters == [
        {
            "$or": [
                {"repo": {"$eq": "repo1"}},
                {"repo": {"$eq": "repo2"}},
                {"repo": {"$eq": "repo3"}},
            ]
        }
    ]
