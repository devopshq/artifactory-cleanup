import inspect
import json
import sys
from copy import deepcopy
from datetime import date
from typing import Optional, Union, List, Dict
from urllib.parse import quote
from requests import HTTPError

import cfgv
from hurry.filesize import size

from artifactory_cleanup.base_url_session import BaseUrlSession

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class ArtifactDict(TypedDict):
    repo: str
    path: str
    name: str
    properties: dict
    stats: dict
    size: int
    actual_sha1: str


class ArtifactsList(List[ArtifactDict]):
    def keep(self, artifacts):
        """Just a shortcut for better readability"""
        return self.remove(artifacts)

    def remove(self, artifacts: Union[ArtifactDict, List[ArtifactDict]]) -> None:
        """
        Remove artifacts (or one artifact) and log that.
        """
        if not isinstance(artifacts, list):
            artifacts = [artifacts]

        for artifact in artifacts:
            print(f"Filter package {artifact['path']}/{artifact['name']}")
            super().remove(artifact)

    @classmethod
    def from_response(cls, artifacts: List[Dict]) -> "ArtifactsList":
        """
        :param artifacts: Pure AQL response
        """
        return ArtifactsList(cls.prepare(artifact) for artifact in artifacts)

    @classmethod
    def prepare(cls, artifact: Dict) -> ArtifactDict:
        """
        Convert properties, stat from the list format to the dict format
        """
        if "properties" in artifact:
            if not isinstance(artifact["properties"], dict):
                artifact["properties"] = {
                    x["key"]: x.get("value") for x in artifact["properties"]
                }
        else:
            artifact["properties"] = {}

        if "stats" in artifact:
            artifact["stats"] = artifact["stats"][0]
        else:
            artifact["stats"] = {}

        return artifact


class Rule(object):
    """
    Rule contains a logic how we get artifacts to remove.

    Follow Unix philosophy when you're building new Rule: https://en.wikipedia.org/wiki/Unix_philosophy
    Make it small and then combine them in CleanupPolicy in more complicated entities.
    """

    session: Optional[BaseUrlSession] = None
    today: date = None

    # You can overwrite checks for config file
    schema: Optional[List[cfgv.Conditional]] = None

    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    def title(cls) -> str:
        """Cut the docstring to show only the very first important line"""
        if not cls.__doc__:
            return ""
        return [x.strip() for x in cls.__doc__.splitlines() if x][0]

    def init(self, session, today, *args, **kwargs) -> None:
        """
        Init the rule after got all information.

        Please make sure to add *args, **kwargs for future extension
        """
        self.session = session
        self.today = today

    def check(self, *args, **kwargs):
        """
        Checks that Rule is configured right.
        Make sure to add args, kwargs, because we can add more options there in the future
        """

    def aql_add_filter(self, filters: List) -> List:
        """
        Add one or more filters to `<domain>.find(<filters>)` AQL part.
        It's called <criteria> in the documentation: <domain_query>.find(<criteria>)
        https://www.jfrog.com/confluence/display/JFROG/Artifactory+Query+Language#usage

        The artifacts will be filtered on Artifactory side.
        It's better to filter out as much as possible with that filter
        rather than get all artifacts and filter out them in memory because it leads to a heavy response from Artifactory

        You can detect any conflicts with others rules here, if they conflict on AQL level.
        """
        return filters

    def aql_add_text(self, aql: str) -> str:
        """
        You can change AQL text after applying all rules filters.

        You can apply sort rules and other AQL filter here.
        https://www.jfrog.com/confluence/display/JFROG/Artifactory+Query+Language
        """
        return aql

    def filter(self, artifacts: ArtifactsList) -> ArtifactsList:
        """
        Filter artifacts after performing AQL query.
        To keep artifacts - use `artifacts.remove(artifacts_to_keep)` method.

        If you have your own logic - please overwrite the method in your Rule class.
        Here you can filter artifacts in memory, make additional calls to Artifactory or even call other services!

        :param artifacts: Filtered artifacts list that we get after filter them with AQL
        :return List of artifacts that you are going to remove
        """
        return artifacts


class CleanupPolicy(object):
    """

    If you need one rule for the repository you can set the rule as shown below::

        CleanupPolicy(
           'myrepo.snapshot',
           rules.repo,
           rules.DeleteOlderThan(days=7),
        )
    """

    # domain_query in https://www.jfrog.com/confluence/display/JFROG/Artifactory+Query+Language#usage
    DOMAIN = "items"

    session: Optional[BaseUrlSession] = None
    today: date = None

    def __init__(self, name: str, *rules: Rule):
        if not isinstance(name, str):
            raise ValueError(
                "Bad CleanupPolicy, first argument must be name.\n"
                f"You called: CleanupPolicy(name={name}, *rules={rules})"
            )

        self.name = name
        self.rules = list(rules)
        self.aql_text = None

        # init object if passed not initialized class
        # for `rules.repo` rule, see above in the docstring
        for i, rule in enumerate(self.rules):
            if inspect.isclass(rule):
                self.rules[i] = rule(self.name)

    def check(self, *args, **kwargs) -> None:
        """
        Check that we're ready to run the policy.
        Here you can call additional APIs to check they're available or check that rules are consistent,
        like have no contradictory rules in one set
        """
        for rule in self.rules:
            self._check_rules_are_updated(rule)
            try:
                rule.check(*args, **kwargs)
            except Exception as exc:
                print(
                    f"Check failed for rule '{rule.name()}' in policy '{self.name}':",
                    file=sys.stdout,
                )
                print(exc, file=sys.stdout)
                sys.exit(1)

    def _check_rules_are_updated(self, rule):
        # Make sure people update their own rules to the latest interface
        # 0.4 => 1.0.0
        old_attributes = ("_aql_add_filter", "_aql_add_text", "_filter_result")
        old_rule = any(hasattr(rule, attr) for attr in old_attributes)
        if old_rule:
            raise ValueError(
                f"Please update the Rule '{rule.name()()}' to the new Rule API.\n"
                "- Read CHANGELOG.md https://github.com/devopshq/artifactory-cleanup/blob/master/CHANGELOG.md\n"
                "- Read README.md https://github.com/devopshq/artifactory-cleanup#readme"
            )

    def init(self, session, today) -> None:
        """
        Set properties and apply them to all rules
        """
        self.session = session
        self.today = today

        for rule in self.rules:
            rule.init(session, today)

    def build_aql_query(self) -> None:
        """
        Collect all aql queries into a single list so that the rules check for conflicts among themselves
        """
        aql_find_filters = self._get_aql_find_filters()
        self.aql_text = self._get_aql_text(aql_find_filters)
        print("*" * 80)
        print("Result AQL Query:")
        print(self.aql_text)
        print("*" * 80)

    def _get_aql_find_filters(self) -> Dict:
        """Go over all rules and get .find filters"""
        filters = []
        for rule in self.rules:
            before_query_list = deepcopy(filters)
            print(f"Add AQL Filter - rule: {rule.name()} - {rule.title()}")
            filters = rule.aql_add_filter(filters)
            if before_query_list != filters:
                print("Before AQL query: {}".format(before_query_list))
                print("After AQL query: {}".format(filters))
                print()
        return {"$and": filters}

    def _get_aql_text(self, find_filters: Dict) -> str:
        """
        Collect from all rules additional texts of requests
        """
        filters_text = json.dumps(find_filters)
        aql = f'{self.DOMAIN}.find({filters_text}).include("*", "property", "stat")'

        for rule in self.rules:
            before_aql = aql
            print(f"Add AQL Text - rule: {rule.name()} - {rule.title()}")
            aql = rule.aql_add_text(aql)
            if before_aql != aql:
                print("Before AQL text: {}".format(before_aql))
                print("After AQL text: {}".format(aql))
                print()
        return aql

    def get_artifacts(self) -> ArtifactsList:
        """
        Get artifacts from Artifactory by AQL filters that we collect from all rules in the policy
        :return list of artifacts
        """
        assert self.aql_text, "Call build_aql_query before calling get_artifacts"
        r = self.session.post("/api/search/aql", data=self.aql_text)
        r.raise_for_status()
        content = r.json()
        artifacts = content["results"]
        return ArtifactsList.from_response(artifacts)

    def filter(self, artifacts: ArtifactsList) -> ArtifactsList:
        """
        Filter artifacts again all rules
        """
        for rule in self.rules:
            before = len(artifacts)
            print(f"Filter artifacts - rule: {rule.name()} - {rule.title()}")
            artifacts = rule.filter(artifacts)

            if not isinstance(artifacts, ArtifactsList):
                raise ValueError(f"`{rule.name()}` rule must return ArtifactsList")

            if before != len(artifacts):
                print(f"Before count: {before}")
                print(f"After count: {len(artifacts)}")
                print()
        return artifacts

    def delete(self, artifact: ArtifactDict, destroy: bool, ignore_not_found: bool = False) -> None:
        """
        Delete the artifact
        :param artifact: artifact to remove
        :param destroy: if False - just log the action, do not actually remove the artifact
        :param display_format: specify the format string for the file to delete, for example "'{path}' - {size}"
        :param ignore_not_found: if True - do not raise an error if the artifact is not found
        """

        if artifact["path"] == ".":
            path = "{repo}/{name}"
        else:
            path = "{repo}/{path}/{name}"

        artifact_path = path.format(**artifact)
        artifact_path = quote(artifact_path)
        artifact_size = artifact.get("size", 0) or 0
        artifact_hash = artifact.get("actual_sha1", "")

        if not destroy:
            print(f"DEBUG - we would delete '{artifact_path}' ({artifact_hash}) - {size(artifact_size)}")
            return
        print(f"DESTROY MODE - delete '{artifact_path}' ({artifact_hash}) - {size(artifact_size)}")
        r = self.session.delete(artifact_path)
        try:
            r.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 404 and ignore_not_found:
                print(f"NOT FOUND - '{artifact_path}' was not found, so not deleted.")
                return
            raise

