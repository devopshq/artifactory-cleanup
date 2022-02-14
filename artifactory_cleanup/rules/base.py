import inspect
import json
import re
from urllib.parse import quote
from collections import namedtuple


class Rule(object):
    """Parent class. Other rules are inherited from this class."""

    artifactory_session = None
    artifactory_server = None

    def init(self, artifactory_session, artifactory_server, today):
        self.artifactory_session = artifactory_session
        self.artifactory_server = artifactory_server
        self.today = today

    def _aql_add_filter(self, aql_query_list):
        """Executed before an AQL query. Adds the required fields to the query"""
        return aql_query_list

    def _filter_result(self, result_artifact):
        """Filters artifacts according to some rule"""
        return result_artifact

    def _aql_add_text(self, aql_text):
        """Adds text to the end of an AQL query"""
        return aql_text

    def remove_artifact(self, artifacts, result_artifact):
        """Displays artifacts that have been filtered"""
        if not isinstance(artifacts, list):
            artifacts = [artifacts]
        for artifact in artifacts:
            print("Filter package {path}/{name}".format(**artifact))
            result_artifact.remove(artifact)

    def aql_add_filter(self, aql_query_list):
        """Adds a filter to an AQL query"""
        print(
            "Add AQL Filter - rule: {} - {}".format(
                self.__class__.__name__, self.little_doc
            )
        )
        new_aql_query_list = self._aql_add_filter(aql_query_list)
        if aql_query_list != new_aql_query_list:
            print("Before AQL query: {}".format(aql_query_list))
            print("After AQL query: {}".format(new_aql_query_list))
            print()
        return new_aql_query_list

    def aql_add_text(self, aql_text):
        """Adds some expression to AQL query"""
        print(
            "Add AQL Text - rule: {} - {}".format(
                self.__class__.__name__, self.little_doc
            )
        )
        new_aql_text = self._aql_add_text(aql_text)
        if new_aql_text != aql_text:
            print("Before AQL text: {}".format(aql_text))
            print("After AQL text: {}".format(new_aql_text))
            print()
        return new_aql_text

    def filter_result(self, result_artifacts):
        """Filters received data from AQL"""
        print(
            "Filter artifacts - rule: {} - {}".format(
                self.__class__.__name__, self.little_doc
            )
        )
        new_result = self._filter_result(result_artifacts)
        if len(new_result) != len(result_artifacts):
            print("Before count: {}".format(len(result_artifacts)))
            print("After count: {}".format(len(new_result)))
            print()

        return new_result

    @property
    def little_doc(self):
        # Образем всю документацию чтобы принтануть только первую самую важные строчку - что делает это правило
        docs = [x.strip() for x in self.__doc__.splitlines() if x][0]
        return docs

    @classmethod
    def prepare_artifact(cls, artifacts):
        """properties, stat are given in list format, convert them to dict format"""
        all_artifacts = []
        for artifact in artifacts:
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

            all_artifacts.append(artifact)

        return all_artifacts


class CleanupPolicy(object):
    """

    If you need one rule for the repository you can set the rule as shown below::

        CleanupPolicy(
           'myrepo.snapshot',
           rules.repo,
           rules.delete_older_than(days=7),
        )

    """

    def __init__(self, name, *args):
        if not isinstance(name, str):
            raise Exception(
                "Bad CleanupPolicy, first argument must be name.\n"
                "CleanupPolicy argument: name={}, *args={}".format(name, args)
            )
        self.name = name
        self.rules = list(args)

        # init object if passed not initialized class
        # See docstring
        for i, rule in enumerate(self.rules):
            if inspect.isclass(rule):
                self.rules[i] = rule(self.name)

        # Defined in self.init() function
        self.artifactory_session = None
        self.artifactory_url = None
        self.today = None

        # Defined in aql_filter
        self.aql_query_list = []

    def init(self, artifactory_session, artifactory_url, today):
        """
        Set properties and set them to all rules

        :param artifactory_session:
        :param artifactory_url:
        :return:
        """
        self.artifactory_session = artifactory_session
        self.artifactory_url = artifactory_url
        self.today = today

        for rule in self.rules:
            rule.init(artifactory_session, artifactory_url, today)

    def aql_filter(self):
        """
        Collect all aql queries into a single list so that the rules check for conflicts among themselves
        """
        for rule in self.rules:
            self.aql_query_list = rule.aql_add_filter(self.aql_query_list)

    @property
    def aql_text(self):
        """
        Сollect from all rules additional texts of requests
        """
        aql_query_dict = {"$and": self.aql_query_list}
        aql_text = 'items.find({query_dict}).include("*", "property", "stat")'.format(
            query_dict=json.dumps(aql_query_dict)
        )

        for rule in self.rules:
            aql_text = rule.aql_add_text(aql_text)
        return aql_text

    def get_artifacts(self):
        aql_url = "{}/api/search/aql".format(self.artifactory_url)
        _art_auth_etc = {"data": self.aql_text}
        r = self.artifactory_session.post(aql_url, **_art_auth_etc)
        r.raise_for_status()
        content = r.json()
        artifacts = content["results"]

        # properties, stat отдаются в формате list, переделываем их в формат dict
        artifacts = Rule.prepare_artifact(artifacts)

        # Сортируем по пути и имени
        artifacts = sorted(artifacts, key=lambda x: x["path"])
        return artifacts

    def filter(self, artifacts):
        for rule in self.rules:
            artifacts = rule.filter_result(artifacts)
        return artifacts

    def delete(self, artifact, destroy):
        artifact_path = quote("{repo}/{path}/{name}".format(**artifact))
        if destroy:
            print("DESTROY MODE - delete {}".format(artifact_path))
            delete_url = "{}/{}".format(self.artifactory_url, artifact_path)
            r = self.artifactory_session.delete(delete_url)
            r.raise_for_status()
        else:
            print("DEBUG - delete {}".format(artifact_path))


def symbols_to_nuget(
    artifact_name, symbols_to_nuget_reqexp=r"^(.*?)\.(\d+.*)\.symbols.tar.gz"
):
    m = re.match(symbols_to_nuget_reqexp, artifact_name)
    name = version = None
    if m:
        name = m.group(1)
        version = m.group(2)

    return name, version


CrossPackage = namedtuple("CrossPackage", ["name", "branch", "version"])


def parse_cross(artifact):
    m = re.match(
        r"(?P<package>\S*)/(?P<branch>\S*)/(?P<version>[0-9.]+)/.*/(?P=package)[_.-]*(?P=version)?.tar.gz",
        artifact,
    )
    if m:
        name = m.group("package")
        branch = m.group("branch")
        version = m.group("version")
        return CrossPackage(name, branch, version)

    return None


def parse_cross_any_extenstion(artifact):
    m = re.match(
        r"(?P<package>\S*)/(?P<branch>\S*)/(?P<version>[0-9.]+)/"
        r".*/(?P=package)[_.-]*(?P=version)?-*(?P=branch)*",
        artifact,
    )
    if m:
        name = m.group("package")
        branch = m.group("branch")
        version = m.group("version")
        return CrossPackage(name, branch, version)

    return None
