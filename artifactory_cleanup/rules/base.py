import inspect
import json
from urllib.parse import quote


class Rule(object):
    """
    Rule contains a logic how we get artifacts to remove.

    Follow Unix philosophy when you're building new Rule: https://en.wikipedia.org/wiki/Unix_philosophy
    Make it small and then combine them in CleanupPolicy in more complicated entities.
    """

    def __init__(self):
        self.artifactory_session = None
        self.artifactory_server = None
        self.today = None

    def init(self, artifactory_session, artifactory_server, today):
        """
        Init the rule after got all information
        """
        self.artifactory_session = artifactory_session
        self.artifactory_server = artifactory_server
        self.today = today

    def _aql_add_filter(self, aql_query_list):
        """
        Add filter to `items.find` AQL part.

        Here you can filter artifacts on Artifactory side with AQL:
        https://www.jfrog.com/confluence/display/JFROG/Artifactory+Query+Language

        It's better to filter out as much as possible with that filter
        rather than get all artifacts and filter out them in memory because it leads to a heavy response from Artifactory

        Also, you can find any conflicts with others rules here, if they conflict on AQL level
        """
        return aql_query_list

    def _aql_add_text(self, aql_text):
        """
        Change AQL text after applying all rules filters
        """
        return aql_text

    def _filter_result(self, result_artifact):
        """
        Filter artifacts after performing AQL query.
        To remove artifacts from the list - please use Rule.remove_artifact method in order to log the action as well.

        If you have your own logic - please overwrite the method in your Rule class.
        Here you can filter artifacts in memory, make additional calls to Artifactory or even call other services!

        :param result_artifact: Filtered artifacts list that we get after filter them with AQL
        :return List of artifacts that you are going to remove
        """
        return result_artifact

    @staticmethod
    def remove_artifact(artifacts, result_artifact):
        """
        Remove and log artifacts
        :param artifacts: Artifacts to remove
        :param result_artifact: Artifacts remove from it
        """
        if not isinstance(artifacts, list):
            artifacts = [artifacts]
        for artifact in artifacts:
            print(f"Filter package {artifact['path']}/{artifact['name']}")
            result_artifact.remove(artifact)

    def aql_add_filter(self, aql_query_list):
        """
        Add filters to `items.find` AQL part
        """
        print(f"Add AQL Filter - rule: {self.__class__.__name__} - {self.little_doc}")
        new_aql_query_list = self._aql_add_filter(aql_query_list)
        if aql_query_list != new_aql_query_list:
            print("Before AQL query: {}".format(aql_query_list))
            print("After AQL query: {}".format(new_aql_query_list))
            print()
        return new_aql_query_list

    def aql_add_text(self, aql_text):
        """
        Adds some expression to AQL query
        """
        print(f"Add AQL Text - rule: {self.__class__.__name__} - {self.little_doc}")
        new_aql_text = self._aql_add_text(aql_text)
        if new_aql_text != aql_text:
            print("Before AQL text: {}".format(aql_text))
            print("After AQL text: {}".format(new_aql_text))
            print()
        return new_aql_text

    def filter_result(self, result_artifacts):
        """
        Filter artifacts after performing AQL query

        It's a high level function, if you want to specify your own logic
        please overwrite in your Rule class `_filter_result` method
        """
        print(f"Filter artifacts - rule: {self.__class__.__name__} - {self.little_doc}")
        new_result = self._filter_result(result_artifacts)
        if len(new_result) != len(result_artifacts):
            print("Before count: {}".format(len(result_artifacts)))
            print("After count: {}".format(len(new_result)))
            print()

        return new_result

    @property
    def little_doc(self):
        """
        Cut the docstring to show only the very first important line
        """
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
           rules.DeleteOlderThan(days=7),
        )

    """

    def __init__(self, name, *rules):
        if not isinstance(name, str):
            raise Exception(
                "Bad CleanupPolicy, first argument must be name.\n"
                "CleanupPolicy argument: name={}, *args={}".format(name, rules)
            )
        self.name = name
        self.rules = list(rules)

        # init object if passed not initialized class
        # for `rules.repo` rule
        for i, rule in enumerate(self.rules):
            if inspect.isclass(rule):
                self.rules[i] = rule(self.name)

        # Assigned in self.init() function
        self.artifactory_session = None
        self.artifactory_url = None
        self.today = None

        # Defined in aql_filter
        self.aql_query_list = []

    def init(self, artifactory_session, artifactory_url, today):
        """
        Set properties and apply them to all rules
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
        Collect from all rules additional texts of requests
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
        r = self.artifactory_session.post(aql_url, data=self.aql_text)
        r.raise_for_status()
        content = r.json()
        artifacts = content["results"]
        artifacts = Rule.prepare_artifact(artifacts)
        artifacts = sorted(artifacts, key=lambda x: x["path"])
        return artifacts

    def filter(self, artifacts):
        """
        Filter artifacts again all rules
        """
        for rule in self.rules:
            artifacts = rule.filter_result(artifacts)
        return artifacts

    def delete(self, artifact, destroy):
        """
        Delete the artifact
        :param artifact: artifact to remove
        :param destroy: if False - just log the action, do not actually remove the artifact
        :return:
        """
        if artifact["path"] == ".":
            artifact_path = "{repo}/{name}".format(**artifact)
        else:
            artifact_path = "{repo}/{path}/{name}".format(**artifact)

        artifact_path = quote(artifact_path)
        if destroy:
            print("DESTROY MODE - delete {}".format(artifact_path))
            delete_url = "{}/{}".format(self.artifactory_url, artifact_path)
            r = self.artifactory_session.delete(delete_url)
            r.raise_for_status()
        else:
            print("DEBUG - delete {}".format(artifact_path))
