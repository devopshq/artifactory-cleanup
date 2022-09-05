from datetime import date
from typing import List, Iterator

from attr import dataclass
from requests import Session

from artifactory_cleanup.errors import ArtifactoryCleanupException
from artifactory_cleanup.rules.base import CleanupPolicy, ArtifactDict


@dataclass
class CleanupSummary:
    policy_name: str
    artifacts_removed: int
    artifacts_size: int


class ArtifactoryCleanup:
    def __init__(
        self,
        session: Session,
        policies: List[CleanupPolicy],
        destroy: bool,
        today: date,
    ):
        self.session = session
        self.policies = policies
        self.destroy = destroy

        self._init_policies(today)

    def _init_policies(self, today):
        for policy in self.policies:
            policy.init(self.session, today)

    def cleanup(self, block_ctx_mgr, test_ctx_mgr) -> Iterator[CleanupSummary]:
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
                for artifact in artifacts_to_remove:
                    with test_ctx_mgr(get_name_for_ci(artifact)):
                        policy.delete(artifact, destroy=self.destroy)

            # Show summary
            print(f"Deleted artifacts count: {len(artifacts_to_remove)}")
            try:
                artifacts_size = sum([x["size"] for x in artifacts_to_remove])
                print("Summary size: {}".format(artifacts_size))
                yield CleanupSummary(
                    policy_name=policy.name,
                    artifacts_size=artifacts_size,
                    artifacts_removed=len(artifacts_to_remove),
                )

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
