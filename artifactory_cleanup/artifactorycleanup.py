from datetime import date
from typing import List, Iterator

from attr import dataclass
from requests import Session

from artifactory_cleanup.rules.base import CleanupPolicy


@dataclass
class CleanupSummary:
    policy_name: str
    artifacts_removed: int
    artifacts_size: int


class ArtifactoryCleanupException(Exception):
    pass


class ArtifactoryCleanup:
    def __init__(
        self,
        server: str,
        session: Session,
        policies: List[CleanupPolicy],
        destroy: bool,
        today: date,
    ):
        self.server = server
        self.session = session
        self.policies = policies
        self.destroy = destroy

        self._init_policies(today)

    def _init_policies(self, today):
        for policy in self.policies:
            policy.init(self.session, self.server, today)

    def cleanup(self, block_ctx_mgr, test_ctx_mgr) -> Iterator[CleanupSummary]:
        for policy in self.policies:
            with block_ctx_mgr(policy.name):
                # prepare
                with block_ctx_mgr("AQL filter"):
                    policy.aql_filter()

                # Get artifacts
                with block_ctx_mgr("Get artifacts"):
                    print("*" * 80)
                    print("AQL Query:")
                    print(policy.aql_text)
                    print("*" * 80)
                    artifacts = policy.get_artifacts()
                print("Found {} artifacts".format(len(artifacts)))

                # Filter
                with block_ctx_mgr("Filter results"):
                    artifacts_to_remove = policy.filter(artifacts)
                print(f"Found {len(artifacts_to_remove)} artifacts AFTER filtering")

                # Delete or debug
                for artifact in artifacts_to_remove:
                    with test_ctx_mgr(get_name_for_ci(artifact)):
                        policy.delete(artifact, destroy=self.destroy)

            # Info
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
            raise ArtifactoryCleanupException(
                f"Rule with name '{policy_name}' not found"
            )


def get_name_for_ci(artifact):
    return "cleanup.{}.{}_{}".format(
        escape(artifact["repo"]),
        escape(artifact["path"]),
        escape(artifact["name"]),
    )


def escape(name):
    """
    Escape name for some CI servers
    """
    return name.replace(".", "_").replace("/", "_")
