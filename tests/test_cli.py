import json
import pytest
from filecmp import cmp

from artifactory_cleanup import ArtifactoryCleanupCLI


def test_help(capsys):
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--help",
        ],
        exit=False,
    )
    stdout, stderr = capsys.readouterr()
    assert "Usage:" in stdout
    assert not stderr
    assert code == 0


@pytest.mark.usefixtures("requests_repo_name_here")
def test_dry_mode(capsys, shared_datadir, requests_mock):
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
    assert "Destroy MODE" not in stdout
    assert (
        "DEBUG - we would delete 'repo-name-here/path/to/file/filename1.json'" in stdout
    )

    assert (
        requests_mock.call_count == 4
    ), "Requests: check repository exists, AQL, NO DELETE  - 2 times"


@pytest.mark.usefixtures("requests_repo_name_here")
def test_destroy(capsys, shared_datadir, requests_mock):
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--config",
            str(shared_datadir / "cleanup.yaml"),
            "--load-rules",
            str(shared_datadir / "myrule.py"),
            "--destroy",
        ],
        exit=False,
    )
    stdout, stderr = capsys.readouterr()
    assert code == 0, stdout
    assert "Destroy MODE" in stdout
    assert "Verbose MODE" not in stdout

    assert (
        requests_mock.call_count == 6
    ), "Requests: check repository exists, AQL, DELETE - 2 times"
    last_request = requests_mock.last_request
    assert last_request.method == "DELETE"
    assert (
        last_request.url
        == "https://repo.example.com/artifactory/repo-name-here/path/to/file/filename1.json"
    )


@pytest.mark.usefixtures("requests_repo_name_here")
def test_output_table(capsys, shared_datadir, requests_mock):
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
    print(stdout)
    assert code == 0, stdout
    assert (
        "| Cleanup Policy                                         | Files count | Size |"
        in stdout
    )


@pytest.mark.usefixtures("requests_repo_name_here")
def test_output_table(capsys, shared_datadir, requests_mock, tmp_path):
    output_file = tmp_path / "output.txt"
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--config",
            str(shared_datadir / "cleanup.yaml"),
            "--load-rules",
            str(shared_datadir / "myrule.py"),
            "--output-format",
            "table",
            "--output",
            str(output_file),
        ],
        exit=False,
    )
    stdout, stderr = capsys.readouterr()
    print(stdout)
    assert code == 0, stdout
    assert cmp(output_file, shared_datadir / "expected_output.txt") is True


@pytest.mark.usefixtures("requests_repo_name_here")
def test_output_json(capsys, shared_datadir, requests_mock, tmp_path):
    output_json = tmp_path / "output.json"
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--config",
            str(shared_datadir / "cleanup.yaml"),
            "--load-rules",
            str(shared_datadir / "myrule.py"),
            "--output-format",
            "json",
            "--output",
            str(output_json),
        ],
        exit=False,
    )
    stdout, stderr = capsys.readouterr()
    assert code == 0, stdout
    with open(output_json, "r") as file:
        assert json.load(file) == {
            "policies": [
                {
                    "name": "Remove all files from repo-name-here older then 7 days",
                    "file_count": 1,
                    "size": 528,
                },
                {"name": "Use your own rules!", "file_count": 1, "size": 528},
            ],
            "total_size": 1056,
        }


@pytest.mark.usefixtures("requests_repo_name_here")
def test_require_output_json(capsys, shared_datadir, requests_mock):
    _, code = ArtifactoryCleanupCLI.run(
        [
            "ArtifactoryCleanupCLI",
            "--config",
            str(shared_datadir / "cleanup.yaml"),
            "--load-rules",
            str(shared_datadir / "myrule.py"),
            "--output-format",
            "json",
        ],
        exit=False,
    )
    assert code == 2, stdout
    stdout, stderr = capsys.readouterr()
    assert (
        "Error: Given --output-format, the following are missing ['output']" in stdout
    )


@pytest.mark.usefixtures("requests_repo_name_here")
def test_display_format_default(capsys, shared_datadir, requests_mock):
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
    print(stdout)
    assert code == 0, stdout
    assert (
            "DEBUG - we would delete 'repo-name-here/path/to/file/filename1.json' (11827853eed40e8b60f5d7e45f2a730915d7704d) - 528B\n"
            in stdout
    )
