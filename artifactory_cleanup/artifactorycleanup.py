import importlib
import logging
import sys
from datetime import timedelta, date

import requests
from hurry.filesize import size
from plumbum import cli
from prettytable import PrettyTable
from requests.auth import HTTPBasicAuth
from artifactory_cleanup.context_managers import get_context_managers
from artifactory_cleanup.rules.base import CleanupPolicy
from artifactory_cleanup.rules.delete import delete_empty_folder


requests.packages.urllib3.disable_warnings()


def init_logging():
    logger_format_string = "%(thread)5s %(module)-20s %(levelname)-8s %(message)s"
    logging.basicConfig(
        level=logging.DEBUG, format=logger_format_string, stream=sys.stdout
    )


class ArtifactoryCleanup(cli.Application):
    _user = cli.SwitchAttr(
        ["--user"],
        help="Login to access to the artifactory",
        mandatory=True,
        envname="ARTIFACTORY_USER",
    )

    _password = cli.SwitchAttr(
        ["--password"],
        help="Password to access to the artifactory",
        mandatory=True,
        envname="ARTIFACTORY_PASSWORD",
    )

    _policy_name = cli.SwitchAttr(
        ["--policy-name"], help="Name for a rule", mandatory=False
    )

    _config = cli.SwitchAttr(
        ["--config"], help="Name of config with list of policies", mandatory=False
    )

    _artifactory_server = cli.SwitchAttr(
        ["--artifactory-server"],
        help="URL to artifactory, e.g: https://arti.example.com/artifactory",
        mandatory=True,
        envname="ARTIFACTORY_SERVER",
    )

    _destroy = cli.Flag("--destroy", help="Remove artifacts", mandatory=False)

    _debug = cli.Flag(
        "--debug",
        help="Only print artifacts that can be deleted with the specified cleaning policies and rules",
        mandatory=False,
    )

    _remove_empty_folder = cli.Flag(
        "--remove-empty-folder", help="Cleaning up empty folders in local repositories"
    )

    _days_in_future = cli.SwitchAttr(
        "--days-in-future",
        help="Simulate future behaviour",
        mandatory=False,
        excludes=["--destroy"],
    )

    def _destroy_or_verbose(self):
        if self._destroy:
            print("*" * 80)
            print("Delete MODE")
        else:
            print("*" * 80)
            print("Verbose MODE")

    def main(self):
        # remove trailing slash
        self._artifactory_server = self._artifactory_server.rstrip("/")
        if self._remove_empty_folder:
            rules = [
                CleanupPolicy(
                    "Cleaning up empty folders in local repositories",
                    delete_empty_folder(),
                )
            ]
        else:
            try:
                self._config = self._config.replace(".py", "")
                sys.path.append(".")
                rules = getattr(importlib.import_module(self._config), "RULES")
            except ImportError as error:
                print("Error: {}".format(error))
                exit(1)

        self._destroy_or_verbose()

        if self._days_in_future:
            self._today = date.today() + timedelta(days=int(self._days_in_future))
            print(f"Simulating cleanup actions that will occur on {self._today}")
        else:
            self._today = date.today()

        artifactory_session = requests.Session()
        artifactory_session.auth = HTTPBasicAuth(self._user, self._password)

        # Validate that all rules is CleanupPolicy
        for cleanup_rule in rules:
            if not isinstance(cleanup_rule, CleanupPolicy):
                sys.exit(
                    "Rule '{}' is not CleanupPolicy, check this please".format(
                        cleanup_rule
                    )
                )

        if self._policy_name:
            rules = [rule for rule in rules if self._policy_name in rule.name]
            if not rules:
                sys.exit("Rule with name '{}' does not found".format(self._policy_name))

        table = PrettyTable()
        table.field_names = ["Cleanup Policy", "Files count", "Size"]
        table.align["Cleanup Policy"] = "l"
        total_size = 0

        ctx_mgr_block, ctx_mgr_test = get_context_managers()

        for cleanup_rule in rules:  # type: CleanupPolicy
            with ctx_mgr_block(cleanup_rule.name):
                cleanup_rule.init(
                    artifactory_session, self._artifactory_server, self._today
                )

                # prepare
                with ctx_mgr_block("AQL filter"):
                    cleanup_rule.aql_filter()

                # Get artifacts
                with ctx_mgr_block("Get artifacts"):
                    print("*" * 80)
                    print("AQL Query:")
                    print(cleanup_rule.aql_text)
                    print("*" * 80)
                    artifacts = cleanup_rule.get_artifacts()
                print("Found {} artifacts".format(len(artifacts)))

                # Filter
                with ctx_mgr_block("Filter results"):
                    artifacts_to_remove = cleanup_rule.filter(artifacts)
                print(
                    "Found {} artifacts AFTER filtering".format(
                        len(artifacts_to_remove)
                    )
                )

                # Delete or debug
                for artifact in artifacts_to_remove:
                    # test name for teamcity
                    repo_underscore = (
                        artifact["repo"].replace(".", "_").replace("/", "_")
                    )
                    path_underscore = (
                        artifact["path"].replace(".", "_").replace("/", "_")
                    )
                    name_underscore = (
                        artifact["name"].replace(".", "_").replace("/", "_")
                    )
                    test_name = "cleanup.{}.{}_{}".format(
                        repo_underscore, path_underscore, name_underscore
                    )

                    with ctx_mgr_test(test_name):
                        cleanup_rule.delete(artifact, destroy=self._destroy)

            # Info
            count_artifacts = len(artifacts_to_remove)
            print("Deleted artifacts count: {}".format(count_artifacts))
            try:
                artifacts_size = sum([x["size"] for x in artifacts_to_remove])
                total_size += artifacts_size
                artifacts_size = size(artifacts_size)
                print("Summary size: {}".format(artifacts_size))

                table.add_row([cleanup_rule.name, count_artifacts, artifacts_size])
            except KeyError:
                print("Summary size not defined")
            print()

        table.add_row(["", "", ""])
        table.add_row(["Total size: {}".format(size(total_size)), "", ""])
        print(table)


if __name__ == "__main__":
    init_logging()
    ArtifactoryCleanup.run()
