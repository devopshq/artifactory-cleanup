import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import List, Tuple, Type

import yaml

from artifactory_cleanup import rules
from artifactory_cleanup.rules import Repo
from artifactory_cleanup.rules.base import CleanupPolicy, Rule

logger = logging.getLogger("artifactory-cleanup")


class YamlConfigLoader:
    """
    Load configuration and policies from yaml file
    """

    _rules = {}

    def __init__(self, filepath):
        self.filepath = Path(filepath)

    def get_policies(self) -> List[CleanupPolicy]:
        config = yaml.safe_load(self.filepath.read_text())
        policies = []

        for policy_data in config["artifactory-cleanup"]["policies"]:
            policy_name = policy_data["name"]
            rules = []
            for rule_data in policy_data["rules"]:
                rule = self._build_rule(rule_data)
                rules.append(rule)
            policy = CleanupPolicy(policy_name, *rules)
            policies.append(policy)
        return policies

    def _build_rule(self, rule_data) -> Rule:
        rule_cls = self._rules[rule_data.pop("rule")]

        # For Repo rule, CleanupPolicy initialize it later with the name of the policy
        if rule_cls == Repo and not rule_data:
            return rule_cls

        return rule_cls(**rule_data)

    @classmethod
    def register(cls, rule: Type[Rule], name=None, warning=False):
        name = name or rule.name()
        if name in cls._rules and warning:
            logger.warning(f"Rule with a name '{name}' has been registered before.")
            return
        cls._rules[name] = rule

    @classmethod
    def register_all_builtin_rules(cls):
        for name, obj in vars(rules).items():
            if inspect.isclass(obj) and issubclass(obj, Rule):
                YamlConfigLoader.register(obj, warning=True)


YamlConfigLoader.register_all_builtin_rules()


class PythonPoliciesLoader:
    """
    Load policies and rules from python file
    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)

    def get_policies(self) -> List[CleanupPolicy]:
        try:
            policies_directory = self.filepath.parent
            # Get module name without the py suffix: policies.py => policies
            module_name = self.filepath.stem
            sys.path.append(str(policies_directory))
            policies = getattr(importlib.import_module(module_name), "RULES")

            # Validate that all policies is CleanupPolicy
            for policy in policies:
                if not isinstance(policy, CleanupPolicy):
                    sys.exit(f"Policy '{policy}' is not CleanupPolicy, check it please")

            return policies
        except ImportError as error:
            print("Error: {}".format(error))
            sys.exit(1)


class CliConnectionLoader:
    """Get connection information from cli"""

    def __init__(self, cli):
        self.cli = cli

    def get_connection(self) -> Tuple[str, str, str]:
        return self.cli._artifactory_server, self.cli._user, self.cli._password
