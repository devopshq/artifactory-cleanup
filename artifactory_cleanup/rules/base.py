import inspect
import json
from copy import deepcopy
from typing import Optional
from urllib.parse import quote

import pydash

from artifactory_cleanup.base_url_session import BaseUrlSession


class Rule(object):
    """
    Rule contains a logic how we get artifacts to remove.

    Follow Unix philosophy when you're building new Rule: https://en.wikipedia.org/wiki/Unix_philosophy
    Make it small and then combine them in CleanupPolicy in more complicated entities.
    """

    def __init__(self):
        self.session = None
        self.today = None

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def title(self):
        """Cut the docstring to show only the very first important line"""
        docs = [x.strip() for x in self.__doc__.splitlines() if x][0]
        return docs

    def init(self, session, today, *args, **kwargs):
        """
        Init the rule after got all information.

        Please make sure to add *args, **kwargs for future extension
        """
        self.session = session
        self.today = today

    def aql_add_filter(self, items_find_filters):
        """
        Add filter to `items.find` AQL part.

        Here you can filter artifacts on Artifactory side with AQL:
        https://www.jfrog.com/confluence/display/JFROG/Artifactory+Query+Language

        It's better to filter out as much as possible with that filter
        rather than get all artifacts and filter out them in memory because it leads to a heavy response from Artifactory

        Also, you can find any conflicts with others rules here, if they conflict on AQL level
        """
        return items_find_filters

    def aql_add_text(self, aql):
        """
        You can change AQL text after applying all rules filters.

        You can apply sort rules and other AQL filter here.
        https://www.jfrog.com/confluence/display/JFROG/Artifactory+Query+Language
        """
        return aql

    def filter(self, artifacts):
        """
        Filter artifacts after performing AQL query.
        To remove artifacts from the list (keep artifact) - please use Rule.remove_artifact method in order to log the action as well.

        If you have your own logic - please overwrite the method in your Rule class.
        Here you can filter artifacts in memory, make additional calls to Artifactory or even call other services!

        :param artifacts: Filtered artifacts list that we get after filter them with AQL
        :return List of artifacts that you are going to remove
        """
        return artifacts

    @staticmethod
    def remove_artifact(artifacts_to_remove, artifacts):
        """
        Remove and log artifacts
        :param artifacts: Artifacts to remove
        :param artifacts: Artifacts remove from it
        """
        if not isinstance(artifacts_to_remove, list):
            artifacts_to_remove = [artifacts_to_remove]

        for artifact in artifacts_to_remove:
            print(f"Filter package {artifact['path']}/{artifact['name']}")
            artifacts.remove(artifact)


class CleanupPolicy(object):
    """

    If you need one rule for the repository you can set the rule as shown below::

        CleanupPolicy(
           'myrepo.snapshot',
           rules.repo,
           rules.DeleteOlderThan(days=7),
        )

    """

    def __init__(self, name, *rules):
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

        # Will be assigned in init() function later
        self.session: Optional[BaseUrlSession] = None
        self.today = None

    def init(self, session, today):
        """
        Set properties and apply them to all rules
        """
        self.session = session
        self.today = today

        for rule in self.rules:
            # Make sure people update their own rules to the latest interface
            # 0.4 => 1.0.0
            if hasattr(rule, "_aql_add_filter"):
                raise ValueError(
                    f"Please update the Rule '{rule.name}' to the new Rule API.\n"
                    "- Read CHANGELOG.md https://github.com/devopshq/artifactory-cleanup/blob/master/CHANGELOG.md\n"
                    "- Read README.md https://github.com/devopshq/artifactory-cleanup#readme"
                )

            rule.init(session, today)

    def build_aql_query(self):
        """
        Collect all aql queries into a single list so that the rules check for conflicts among themselves
        """
        aql_items_find_filters = self._get_aql_items_find_filters()
        self.aql_text = self._get_aql_text(aql_items_find_filters)
        print("*" * 80)
        print("Result AQL Query:")
        print(self.aql_text)
        print("*" * 80)

    def _get_aql_items_find_filters(self):
        """Go over all rules and get items.find filters"""
        aql_items_find_filters = []
        for rule in self.rules:
            before_query_list = deepcopy(aql_items_find_filters)
            print(f"Add AQL Filter - rule: {rule.name} - {rule.title}")
            aql_items_find_filters = rule.aql_add_items_find_filters(
                aql_items_find_filters
            )
            if before_query_list != aql_items_find_filters:
                print("Before AQL query: {}".format(before_query_list))
                print("After AQL query: {}".format(aql_items_find_filters))
                print()
        return aql_items_find_filters

    def _get_aql_text(self, aql_items_find_filters):
        """
        Collect from all rules additional texts of requests
        """
        filters = json.dumps({"$and": aql_items_find_filters})
        aql = f'items.find({filters}).include("*", "property", "stat")'

        for rule in self.rules:
            before_aql = aql
            print(f"Add AQL Text - rule: {rule.name} - {rule.title}")
            aql = rule.aql_add_text(aql)
            if before_aql != aql:
                print("Before AQL text: {}".format(before_aql))
                print("After AQL text: {}".format(aql))
                print()
        return aql

    def get_artifacts(self):
        """
        Get artifacts from Artifactory by AQL filters that we collect from all rules in the policy
        :return list of artifacts
        """
        assert self.aql_text, "Call build_aql_query before calling get_artifacts"
        r = self.session.post("/api/search/aql", data=self.aql_text)
        r.raise_for_status()
        content = r.json()
        artifacts = content["results"]
        artifacts = pydash.for_each(artifacts, self.prepare)
        artifacts = pydash.sort(artifacts, key=lambda x: x["path"])
        return artifacts

    def filter(self, artifacts):
        """
        Filter artifacts again all rules
        """
        for rule in self.rules:
            before = len(artifacts)
            print(f"Filter artifacts - rule: {rule.name} - {rule.title}")
            artifacts = rule.filter(artifacts)
            if before != len(artifacts):
                print(f"Before count: {before}")
                print(f"After count: {len(artifacts)}")
                print()
        return artifacts

    def delete(self, artifact, destroy):
        """
        Delete the artifact
        :param artifact: artifact to remove
        :param destroy: if False - just log the action, do not actually remove the artifact
        """
        path = "{repo}/{name}" if artifact["path"] == "." else "{repo}/{path}/{name}"
        artifact_path = path.format(**artifact)
        artifact_path = quote(artifact_path)

        if not destroy:
            print(f"DEBUG - we would delete '{artifact_path}'")
            return

        print(f"DESTROY MODE - delete '{artifact_path}'")
        r = self.session.delete(artifact_path)
        r.raise_for_status()

    @classmethod
    def prepare(cls, artifact):
        """
        Convert properties, stat from the list format to the dict format
        """
        if "properties" in artifact:
            artifact["properties"] = {
                x["key"]: x.get("value") for x in artifact["properties"]
            }
        else:
            artifact["properties"] = {}

        if "stats" in artifact:
            artifact["stats"] = artifact["stats"][0]
        else:
            artifact["stats"] = {}
