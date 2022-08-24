import importlib
import sys
from pathlib import Path
from typing import List, Tuple

from artifactory_cleanup.rules.base import CleanupPolicy


class ConfigLoaderPython:
    """
    Load policies and rules from python file
    """

    @staticmethod
    def load(filename) -> List[CleanupPolicy]:
        try:
            filepath = Path(filename)
            policies_directory = filepath.parent
            # Get module name without the py suffix: policies.py => policies
            module_name = filepath.stem
            sys.path.append(str(policies_directory))
            policies = getattr(importlib.import_module(module_name), "RULES")

            # Validate that all policies is CleanupPolicy
            for policy in policies:
                if not isinstance(policy, CleanupPolicy):
                    sys.exit(f"Rule '{policy}' is not CleanupPolicy, check it please")

            return policies
        except ImportError as error:
            print("Error: {}".format(error))
            sys.exit(1)


class ConfigLoaderCLI:
    def __init__(self, cli):
        self.cli = cli

    def get_connection(self) -> Tuple[str, str, str]:
        # remove trailing slash
        server = self.cli._artifactory_server.rstrip("/")
        return server, self.cli._user, self.cli._password
