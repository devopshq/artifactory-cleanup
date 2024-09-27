import json
import logging
import sys
from datetime import timedelta, date

import requests
from hurry.filesize import size
from plumbum import cli
from plumbum.cli.switches import Set
from prettytable import PrettyTable
from requests.auth import HTTPBasicAuth

from artifactory_cleanup.artifactorycleanup import (
    ArtifactoryCleanup,
)
from artifactory_cleanup.base_url_session import BaseUrlSession
from artifactory_cleanup.context_managers import get_context_managers
from artifactory_cleanup.errors import InvalidConfigError
from artifactory_cleanup.loaders import (
    PythonLoader,
    YamlConfigLoader,
)

requests.packages.urllib3.disable_warnings()


def init_logging():
    logger_format_string = "%(thread)5s %(module)-20s %(levelname)-8s %(message)s"
    logging.basicConfig(
        level=logging.DEBUG, format=logger_format_string, stream=sys.stdout
    )


class ArtifactoryCleanupCLI(cli.Application):
    _config = cli.SwitchAttr(
        ["--config"],
        help="Name of config with list of policies",
        mandatory=False,
        envname="ARTIFACTORY_CLEANUP_CONFIG_FILE",
        default="artifactory-cleanup.yaml",
    )

    _policy = cli.SwitchAttr(
        ["--policy"],
        help="Name for a policy to execute",
        mandatory=False,
    )

    _destroy = cli.Flag(
        "--destroy",
        help="Remove artifacts",
        mandatory=False,
        envname="ARTIFACTORY_CLEANUP_DESTROY",
    )

    _ignore_not_found = cli.Flag(
        "--ignore-not-found",
        help="Ignores 404 errors when deleting artifacts",
        mandatory=False,
        default=False,
        envname="ARTIFACTORY_CLEANUP_IGNORE_NOT_FOUND",
    )

    _worker_count = cli.SwitchAttr(
        "--worker-count",
        help="Number of workers to use",
        mandatory=False,
        default=1,
        envname="ARTIFACTORY_CLEANUP_WORKER_COUNT",
    )

    _days_in_future = cli.SwitchAttr(
        "--days-in-future",
        help="Simulate future behaviour",
        mandatory=False,
        excludes=["--destroy"],
    )

    _load_rules = cli.SwitchAttr(
        "--load-rules",
        help="Load rules from python file",
        mandatory=False,
    )

    _output_file = cli.SwitchAttr(
        "--output", help="Choose the output file", mandatory=False
    )

    _output_format = cli.SwitchAttr(
        "--output-format",
        Set("table", "json", case_sensitive=False),
        help="Choose the output format",
        default="table",
        requires=["--output"],
        mandatory=False,
    )

    _output_artifacts = cli.Flag(
        "--output-artifacts",
        help="When --output-format is json, append the list of all removed artifacts to output",
        mandatory=False,
        default=False,
    )

    @property
    def VERSION(self):
        # To prevent circular imports
        from artifactory_cleanup import __version__

        return __version__

    def _destroy_or_verbose(self):
        print("*" * 80)
        if self._destroy:
            print("Destroy MODE")
        else:
            print("Verbose MODE")

    def _get_today(self):
        today = date.today()
        if self._days_in_future:
            today = today + timedelta(days=int(self._days_in_future))
            print(f"Simulating cleanup actions that will occur on {today}")
        return today

    def _format_table(self, result) -> PrettyTable:
        table = PrettyTable()
        table.field_names = ["Cleanup Policy", "Files count", "Size"]
        table.align["Cleanup Policy"] = "l"

        for policy_result in result["policies"]:
            row = [
                policy_result["name"],
                policy_result["file_count"],
                size(policy_result["size"]),
            ]
            table.add_row(row)

        table.add_row(["", "", ""])
        table.add_row(["Total size: {}".format(size(result["total_size"])), "", ""])
        return table

    def _print_table(self, result: dict):
        print(self._format_table(result))

    def _create_output_file(self, result, filename, format):
        text = ""
        if format == "table":
            text = self._format_table(result).get_string()
        elif format == "json":
            text = json.dumps(result, indent=4)

        with open(filename, "w", encoding="utf-8") as file:
            file.write(text)

    def main(self):
        today = self._get_today()
        if self._load_rules:
            PythonLoader.import_module(self._load_rules)

        loader = YamlConfigLoader(self._config)
        try:
            policies = loader.get_policies()
        except InvalidConfigError as err:
            print("Failed to load config file")
            print(str(err), file=sys.stderr)
            sys.exit(1)

        server, user, password, apikey = loader.get_connection()
        session = BaseUrlSession(server)
        if apikey:
            print("Using API Key")
            headers = {
                "X-JFrog-Art-Api": apikey
            }
            session.headers = headers
        else:
            print("Using user and password")
            session.auth = HTTPBasicAuth(user, password)

        self._destroy_or_verbose()
        print(f"Using {self._worker_count} workers")
        cleanup = ArtifactoryCleanup(
            session=session,
            policies=policies,
            destroy=self._destroy,
            today=today,
            ignore_not_found=self._ignore_not_found,
            worker_count=self._worker_count,
        )

        # Filter policies by name
        if self._policy:
            cleanup.only(self._policy)

        result = {"policies": [], "total_size": 0}
        total_size = 0

        block_ctx_mgr, test_ctx_mgr = get_context_managers()
        for summary in cleanup.cleanup(
            block_ctx_mgr=block_ctx_mgr, test_ctx_mgr=test_ctx_mgr
        ):
            if summary is None:
                continue
            total_size += summary.artifacts_size

            policy = {
                "name": summary.policy_name,
                "file_count": summary.artifacts_removed,
                "size": summary.artifacts_size
            }
            if self._output_artifacts:
                policy["removed_artifacts"] = summary.removed_artifacts
            result["policies"].append(policy)
        result["total_size"] = total_size

        self._print_table(result)

        if self._output_file:
            self._create_output_file(result, self._output_file, self._output_format)


if __name__ == "__main__":
    init_logging()
    ArtifactoryCleanupCLI.run()
