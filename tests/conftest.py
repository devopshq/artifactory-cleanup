import pytest


@pytest.fixture(autouse=True)
def requests_mock_all(requests_mock):
    """
    Mock all HTTP requests outside - only use mocks
    Work for 'requests' library only
    """


def attach_requests_mock_to(mock, server):
    server = server.rstrip("/")
    mock.get(f"{server}/api/storage/repo-name-here")
    mock.post(
        f"{server}/api/search/aql",
        json={
            "results": [
                {
                    "repo": "repo-name-here",
                    "path": "path/to/file",
                    "name": "filename1.json",
                    "type": "file",
                    "size": 528,
                    "created": "2021-03-21T13:54:52.383+02:00",
                    "created_by": "admin",
                    "modified": "2021-03-21T13:54:32.000+02:00",
                    "modified_by": "admin",
                    "updated": "2021-03-21T13:54:52.384+02:00",
                    "actual_sha1": "11827853eed40e8b60f5d7e45f2a730915d7704d",
                    "properties": [
                        {"key": "property-1", "value": "property-value-1"},
                        {"key": "property-2", "value": "property-value-2"},
                    ],
                    "stats": [
                        {
                            "uri": "http://localhost:8081/artifactory/api/storage/libs-release-local/org/acme/foo/1.0/foo-1.0.jar",
                            "downloadCount": 1337,
                            "lastDownloadedBy": "user1",
                        }
                    ],
                },
            ],
            "range": {"start_pos": 0, "end_pos": 12, "total": 12},
        },
    )
    mock.delete(f"{server}/repo-name-here/path/to/file/filename1.json")
    return mock


@pytest.fixture()
def requests_repo_name_here(requests_mock):
    attach_requests_mock_to(requests_mock, "http://example.com/")
    attach_requests_mock_to(requests_mock, "https://repo.example.com/artifactory")
    return requests_mock
