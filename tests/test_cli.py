import pytest

from artifactory_cleanup import ArtifactoryCleanupCLI


def test_help(capsys):
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--help",
        ],
        exit=False,
    )
    assert code == 0


@pytest.mark.usefixtures("requests_repo_name_here")
def test_dry_mode(capsys, shared_datadir, requests_mock):
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--user",
            "user",
            "--password",
            "password",
            "--artifactory-server",
            "http://example.com/",
            "--config",
            str(shared_datadir / "policies.py"),
        ],
        exit=False,
    )
    stdout, stderr = capsys.readouterr()
    assert code == 0, stdout
    assert "Verbose MODE" in stdout
    assert (
        "DEBUG - we would delete 'repo-name-here/path/to/file/filename1.json'" in stdout
    )

    assert (
        requests_mock.call_count == 2
    ), "Requests: check repository exists, AQL, NO DELETE"


@pytest.mark.usefixtures("requests_repo_name_here")
def test_destroy(capsys, shared_datadir, requests_mock):
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--destroy",
            "--user",
            "user",
            "--password",
            "password",
            "--artifactory-server",
            "http://example.com/",
            "--config",
            str(shared_datadir / "policies.py"),
        ],
        exit=False,
    )
    stdout, stderr = capsys.readouterr()
    assert code == 0, stdout
    assert "Destroy MODE" in stdout

    assert (
        requests_mock.call_count == 3
    ), "Requests: check repository exists, AQL, DELETE"
    last_request = requests_mock.last_request
    assert last_request.method == "DELETE"
    assert (
        last_request.url
        == "http://example.com/repo-name-here/path/to/file/filename1.json"
    )


@pytest.mark.usefixtures("requests_repo_name_here")
def test_yaml_config(capsys, shared_datadir, requests_mock):
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--config",
            str(shared_datadir / "cleanup.yaml"),
            "--load-rules",
            str(shared_datadir / "myrule.py"),
        ],
        exit=False,
    )
    stdout, stderr = capsys.readouterr()
    assert code == 0, stdout
    assert "Verbose MODE" in stdout
    assert (
        "DEBUG - we would delete 'repo-name-here/path/to/file/filename1.json'" in stdout
    )

    assert (
        requests_mock.call_count == 4
    ), "Requests: check repository exists, AQL, NO DELETE  - 2 times"
