from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import List, Iterator, Optional

from attr import dataclass
from requests import Session

from artifactory_cleanup.errors import ArtifactoryCleanupException
from artifactory_cleanup.rules.base import ArtifactsList, CleanupPolicy, ArtifactDict


@dataclass
class CleanupSummary:
    policy_name: str
    artifacts_removed: int
    artifacts_size: int
    removed_artifacts: ArtifactsList


class ArtifactoryCleanup:
    def __init__(
        self,
        session: Session,
        policies: List[CleanupPolicy],
        destroy: bool,
        today: date,
        ignore_not_found: bool,
        worker_count: int,
    ):
        self.session = session
        self.policies = policies
        self.destroy = destroy
        self.ignore_not_found = ignore_not_found
        self.worker_count = worker_count

        self._init_policies(today)

    def _init_policies(self, today):
        for policy in self.policies:
            policy.init(self.session, today)

    def cleanup(self, block_ctx_mgr, test_ctx_mgr) -> Iterator[Optional[CleanupSummary]]:
        for policy in self.policies:
            with block_ctx_mgr(policy.name):
                # Prepare
                with block_ctx_mgr("Check"):
                    policy.check()

                with block_ctx_mgr("AQL filter"):
                    policy.build_aql_query()

                # Get artifacts
                with block_ctx_mgr("Get artifacts"):
                    artifacts = policy.get_artifacts()
                print("Found {} artifacts".format(len(artifacts)))

                # Filter artifacts
                with block_ctx_mgr("Filter results"):
                    artifacts_to_remove = policy.filter(artifacts)
                print(f"Found {len(artifacts_to_remove)} artifacts AFTER filtering")

                # Delete artifacts
                def _delete(artifact):
                    with test_ctx_mgr(get_name_for_ci(artifact)):
                        policy.delete(artifact, destroy=self.destroy, ignore_not_found=self.ignore_not_found)

                with ThreadPoolExecutor(max_workers=int(self.worker_count)) as executor:
                    for artifact in artifacts_to_remove:
                        executor.submit(_delete, artifact=artifact)

            # Show summary
            print(f"Deleted artifacts count: {len(artifacts_to_remove)}")
            try:
                artifacts_size = sum([x["size"] for x in artifacts_to_remove])
                print("Summary size: {}".format(artifacts_size))
                summary = CleanupSummary(
                    policy_name=policy.name,
                    artifacts_size=artifacts_size,
                    artifacts_removed=len(artifacts_to_remove),
                    removed_artifacts=artifacts_to_remove
                )
                yield summary
            except KeyError:
                print("Summary size not defined")
                yield None
            print()

    def only(self, policy_name: str):
        """
        Run only one or few the closest policies to the provided name
        """
        policies = [policy for policy in self.policies if policy_name in policy.name]
        if not policies:
            msg = f"Rule with name '{policy_name}' not found"
            raise ArtifactoryCleanupException(msg)

        self.policies = policies


def get_name_for_ci(artifact: ArtifactDict) -> str:
    return "cleanup.{}.{}_{}".format(
        escape(artifact["repo"]),
        escape(artifact["path"]),
        escape(artifact["name"]),
    )


def escape(name: str) -> str:
    """
    Escape name for some CI servers
    """
    return name.replace(".", "_").replace("/", "_")
