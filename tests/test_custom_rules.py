from artifactory_cleanup.rules import Rule


class CustomRuleWithDocs(Rule):
    """Example with doc string"""


class CustomRuleWithoutDocs(Rule):
    pass


def test_custom_rule_with_docstring_adds_to_title():
    rule = CustomRuleWithDocs()
    assert rule.title() == "Example with doc string"


def test_custom_rule_without_docstring():
    rule = CustomRuleWithoutDocs()
    assert rule.title() == ""
