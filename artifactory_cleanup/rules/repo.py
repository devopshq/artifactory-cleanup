from sys import stderr

from requests import HTTPError

from artifactory_cleanup.errors import InvalidConfigError
from artifactory_cleanup.rules.base import Rule, ArtifactsList


class Repo(Rule):
    """
    Apply the policy to one repository.
    """

    schema = []

    def __init__(self, name: str):
        bad_sym = set("*/[]")
        if set(name) & bad_sym:
            raise InvalidConfigError(
                "Bad name for repo: {name}, contains bad symbols: {bad_sym}\n"
                "Check that your have repo() correct".format(
                    name=name, bad_sym="".join(bad_sym)
                )
            )
        self.repo = name

    def check(self, *args, **kwargs):
        print(f"Checking '{self.repo}' repository exists.")
        try:
            url = f"/api/storage/{self.repo}"
            r = self.session.get(url)
            r.raise_for_status()
            print(f"The {self.repo} repository exists.")
        except HTTPError as e:
            stderr.write(f"The {self.repo} repository does not exist!")
            print(e)
            exit(1)

    def aql_add_filter(self, filters):
        filter_ = {
            "repo": {
                "$eq": self.repo,
            }
        }
        filters.append(filter_)
        return filters

    def filter(self, artifacts: ArtifactsList):
        return artifacts


class RepoByMask(Rule):
    """
    Apply rule to repositories matching by mask
    """

    def __init__(self, mask: str):
        self.mask = mask

    def aql_add_filter(self, filters):
        print("Get from {}".format(self.mask))
        filter_ = {
            "repo": {
                "$match": self.mask,
            }
        }
        filters.append(filter_)
        return filters


class PropertyEq(Rule):
    """Deletes repository artifacts with a specific property value only"""

    def __init__(self, property_key, property_value):
        self.property_key = property_key
        self.property_value = property_value

    def aql_add_filter(self, filters):
        filter_ = {
            "$and": [
                {"property.key": {"$eq": self.property_key}},
                {"property.value": {"$eq": self.property_value}},
            ]
        }
        filters.append(filter_)
        return filters


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

    def filter(self, artifacts):
        good_artifact = [
            x
            for x in artifacts
            if x["properties"].get(self.property_key) == self.property_value
        ]
        artifacts.remove(good_artifact)
        return artifacts
