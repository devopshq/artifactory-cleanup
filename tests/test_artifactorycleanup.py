from contextlib import contextmanager
from datetime import date
from unittest.mock import Mock

import pytest

from artifactory_cleanup.artifactorycleanup import ArtifactoryCleanup
from artifactory_cleanup.errors import ArtifactoryCleanupException


@contextmanager
def noop_context_manager(name):
    yield


def test_cleanup_handles_deletion_failure(capsys):
    artifacts = [
        {"repo": "test-repo", "path": "folder", "name": "ok.zip", "size": 10},
        {"repo": "test-repo", "path": "folder", "name": "failed.zip", "size": 20},
    ]

    policy = Mock()
    policy.name = "test-policy"
    policy.get_artifacts.return_value = artifacts
    policy.filter.return_value = artifacts

    def delete(artifact, **kwargs):
        if artifact["name"] == "failed.zip":
            raise RuntimeError("HTTP 500")
        return True

    policy.delete.side_effect = delete

    cleanup = ArtifactoryCleanup(
        session=Mock(),
        policies=[policy],
        destroy=True,
        today=date(2026, 1, 1),
        ignore_not_found=False,
        worker_count=2,
    )

    with pytest.raises(ArtifactoryCleanupException):
        list(
            cleanup.cleanup(
                block_ctx_mgr=noop_context_manager,
                test_ctx_mgr=noop_context_manager,
            )
        )

    output = capsys.readouterr().out

    assert "FAILED -" in output
    assert "failed_zip" in output
    assert "Deleted artifacts count: 1" in output
    assert "Failed deletion count: 1" in output
