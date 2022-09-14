from artifactory_cleanup.rules.utils import to_masks
from artifactory_cleanup.rules.base import Rule


class FilterRule(Rule):
    attribute_name = None
    operator = None
    boolean_operator = None

    def __init__(self, masks):
        if not self.attribute_name:
            raise AttributeError("Attribute 'attribute_name' must be specified")
        if not self.operator:
            raise AttributeError("Attribute 'operator' must be specified")
        if not self.boolean_operator:
            raise AttributeError("Attribute 'boolean_operator' must be specified")

        self.masks = to_masks(masks)

    def aql_add_filter(self, filters):
        rule_list = []
        for mask in self.masks:
            filter_ = {
                self.attribute_name: {
                    self.operator: mask,
                }
            }
            rule_list.append(filter_)
        filters.append({self.boolean_operator: rule_list})
        return super().aql_add_filter(filters)


class IncludePath(FilterRule):
    """
    Apply to artifacts by path / mask.
    """

    attribute_name = "path"
    operator = "$match"
    boolean_operator = "$or"


class IncludeFilename(FilterRule):
    """
    Apply to artifacts by name/mask.
    """

    attribute_name = "name"
    operator = "$match"
    boolean_operator = "$or"


class ExcludePath(FilterRule):
    """
    Exclude artifacts by path.
    """

    attribute_name = "path"
    operator = "$nmatch"
    boolean_operator = "$and"


class ExcludeFilename(FilterRule):
    """
    Exclude artifacts by filename.
    """

    attribute_name = "name"
    operator = "$nmatch"
    boolean_operator = "$and"
