from artifactory_cleanup.rules import (
    KeepLatestNFiles,
    ArtifactsList,
    KeepLatestNFilesInFolder,
)
from tests.utils import makeas


def test_KeepLatestNFiles():
    data = [
        {
            "path": "2.1.1",
            "name": "name.zip",
            "created": "2021-03-20T13:54:52.383+02:00",
        },
        {
            "path": "0.1.100",
            "name": "name.zip",
            "created": "2021-03-19T13:53:52.383+02:00",
        },
        {
            "path": "0.1.200",
            "name": "name.zip",
            "created": "2021-01-19T13:53:52.383+02:00",
        },
        {
            "path": "0.1.99",
            "name": "name.zip",
            "created": "2021-01-19T13:53:52.383+02:00",
        },
        {
            "path": "1.3.1",
            "name": "name.zip",
            "created": "2021-03-20T13:53:52.383+02:00",
        },
    ]

    artifacts = ArtifactsList.from_response(data)

    remove_these = KeepLatestNFiles(2).filter(artifacts)
    expected = [
        {
            "path": "0.1.200",
        },
        {
            "path": "0.1.99",
        },
        {
            "path": "0.1.100",
        },
    ]
    assert makeas(remove_these, expected) == expected


def test_KeepLatestNFilesInFolder():
    data = [
        {
            "path": "folder1",
            "name": "0.0.2.zip",
            "created": "2021-03-20T13:54:52.383+02:00",
        },
        {
            "path": "folder1",
            "name": "0.0.1.zip",
            "created": "2021-03-19T13:53:52.383+02:00",
        },
        {
            "path": "folder2",
            "name": "0.0.1.zip",
            "created": "2021-03-19T13:53:52.383+02:00",
        },
        {
            "path": "folder2",
            "name": "0.0.2.zip",
            "created": "2021-03-20T13:54:52.383+02:00",
        },
        {
            "path": "folder3",
            "name": "0.0.1.zip",
            "created": "2021-03-20T13:54:52.383+02:00",
        },
    ]

    artifacts = ArtifactsList.from_response(data)

    remove_these = KeepLatestNFilesInFolder(1).filter(artifacts)
    expected = [
        {"name": "0.0.1.zip", "path": "folder1"},
        {"name": "0.0.1.zip", "path": "folder2"},
    ]
    assert makeas(remove_these, expected) == expected
