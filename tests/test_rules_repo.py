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
    session = "session"
    today = "today"
    rule.init(session, today, "arg1", "arg2", "arg3", abc=123)
    assert rule.session is None
    assert rule.today is None
    for repo in rule.repos:
        assert repo.session == session
        assert repo.today == today
