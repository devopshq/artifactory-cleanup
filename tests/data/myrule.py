"""
Simple example to show how we can create our own rules in python
"""
from typing import List

from artifactory_cleanup import register
from artifactory_cleanup.rules import Rule, ArtifactsList


class MySimpleRule(Rule):
    """For more methods look at Rule source code"""

    def __init__(self, my_param):
        self.my_param = my_param

    def aql_add_filter(self, filters: List) -> List:
        print(self.my_param)
        return filters

    def filter(self, artifacts: ArtifactsList) -> ArtifactsList:
        """I'm here just to print the list"""
        print(self.my_param)
        return artifacts


# Register your rule in the system
register(MySimpleRule)
