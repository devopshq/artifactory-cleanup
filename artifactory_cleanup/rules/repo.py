import re
from sys import stderr

from requests import HTTPError

from artifactory_cleanup.rules.base import Rule
from artifactory_cleanup.rules.exception import PolicyException


class Repo(Rule):
    """
    Apply the rule to one repository.
    If no name is specified, it is taken from the rule name::

        CleanupPolicy(
           'myrepo.snapshot',
           # if the rule is one for all repositories - you can skip duplicate name
           rules.repo,
           ...
        ),

    """

    def __init__(self, name: str):
        bad_sym = set("*/[]")
        if set(name) & bad_sym:
            raise PolicyException(
                "Bad name for repo: {name}, contains bad symbols: {bad_sym}\n"
                "Check that your have repo() correct".format(
                    name=name, bad_sym="".join(bad_sym)
                )
            )
        self.name = name

    def _aql_add_filter(self, aql_query_list):
        print("Get from {}".format(self.name))
        request_url = "{}/api/storage/{}".format(self.artifactory_server, self.name)
        try:
            print("Checking the existence of the {} repository".format(self.name))
            r = self.artifactory_session.get(request_url)
            r.raise_for_status()
            print("The {} repository exists".format(self.name))
        except HTTPError as e:
            stderr.write("The {} repository does not exist".format(self.name))
            print(e)
            exit(1)

        update_dict = {
            "repo": {
                "$eq": self.name,
            }
        }
        aql_query_list.append(update_dict)
        return aql_query_list


class RepoByMask(Rule):
    """
    Apply rule to repositories matching by mask
    """

    def __init__(self, mask):
        self.mask = mask

    def _aql_add_filter(self, aql_query_list):
        print("Get from {}".format(self.mask))
        update_dict = {
            "repo": {
                "$match": self.mask,
            }
        }
        aql_query_list.append(update_dict)
        return aql_query_list


class RepoByType(Rule):
    """
    Apply rule to repositories of certain type. Only local repositories will be used.
    Valid types:
        bower|cargo|chef|cocoapods|composer|conan|cran|debian|docker|gems|gitlfs|go|gradle|helm|ivy|maven|
        nuget|opkg|pub|puppet|pypi|rpm|sbt|terraform|vagrant|yum|generic
    """

    def __init__(self, repo_type, max_repos=10):
        if not re.compile("^[a-z]+$").match(repo_type):
            raise PolicyException(
                "Bad repo type '{}': only lowercase letters allowed".format(repo_type)
            )
        self.package_type = repo_type
        self.max_repos = max_repos

    def _aql_add_filter(self, aql_query_list):
        repo_names = self._fetch_repo_names()
        update_dict = {"$or": []}
        for repo_name in repo_names:
            update_dict["$or"].append({"repo": {"$eq": repo_name}})
        aql_query_list.append(update_dict)

        return aql_query_list

    def _fetch_repo_names(self):
        print("Getting all repositories of type {}".format(self.package_type))
        request_url = "{}/api/repositories?type=local&packageType={}".format(
            self.artifactory_server, self.package_type
        )
        r = self.artifactory_session.get(request_url)
        r.raise_for_status()
        repos = [x["key"] for x in r.json()]
        if len(repos) < 1:
            stderr.write("No repositories of type {} found".format(self.package_type))
            exit(0)

        return repos


class PropertyEq(Rule):
    """Deletes repository artifacts with a specific property value only"""

    def __init__(self, property_key, property_value):
        self.property_key = property_key
        self.property_value = property_value

    def _aql_add_filter(self, aql_query_list):
        update_dict = {
            "$and": [
                {"property.key": {"$eq": self.property_key}},
                {"property.value": {"$eq": self.property_value}},
            ]
        }
        aql_query_list.append(update_dict)
        return aql_query_list


class PropertyNeq(Rule):
    """
    Delete repository artifacts only if the value is not equal to the specified one.
    If there is no value, delete it anyway.

    You can specify a flag to not delete ``do_not_delete=1``::

        PropertyNeq('do_not_delete", '1')
    """

    def __init__(self, property_key, property_value):
        self.property_key = property_key
        self.property_value = str(property_value)

    def _filter_result(self, result_artifact):
        good_artifact = [
            x
            for x in result_artifact
            if x["properties"].get(self.property_key) == self.property_value
        ]
        self.remove_artifact(good_artifact, result_artifact)
        return result_artifact


# under_score - old style of naming
# Keep it for backward compatibility
repo = Repo
repo_by_mask = RepoByMask
property_eq = PropertyEq
property_neq = PropertyNeq
