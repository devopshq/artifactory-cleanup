from artifactory_cleanup.rules.base import Rule


class IncludePath(Rule):
    """
    Apply to artifacts by path / mask.

    You can specify multiple paths::

       IncludePath('*production*'),
       IncludePath(['*release*', '*master*']),

    """

    def __init__(self, mask):
        self.mask = mask

    def _aql_add_filter(self, aql_query_list):
        update_dict = {
            "path": {
                "$match": self.mask,
            }
        }
        aql_query_list.append(update_dict)
        return aql_query_list


class __FilterDockerImages(Rule):
    operator = None
    boolean_operator = None

    def __init__(self, masks):
        if isinstance(masks, str):
            self.masks = [masks]
        elif isinstance(masks, list):
            self.masks = masks
        else:
            raise AttributeError("Mask must by str|list")

    def _aql_add_filter(self, aql_query_list):
        if not self.operator:
            raise AttributeError("Attribute 'operator' must be specified")

        if not self.boolean_operator:
            raise AttributeError("Attribute 'boolean_operator' must be specified")

        rule_list = []
        for mask in self.masks:
            if ":" not in mask:
                raise AttributeError("Mask '{}' must contain ':'".format(mask))
            # alpine:2.4 => alpine/2.4
            mask = mask.replace(":", "/")
            update_dict = {
                "path": {
                    self.operator: mask,
                }
            }
            rule_list.append(update_dict)

        aql_query_list.append({self.boolean_operator: rule_list})
        return aql_query_list


class IncludeDockerImages(__FilterDockerImages):
    """
    Apply to docker images with the specified names and tags.

    You can specify multiple names and tags::

       IncludeDockerImages('*:production*'),
       IncludeDockerImages(['ubuntu:*', 'debian:9']),

    """

    operator = "$match"
    boolean_operator = "$or"


class ExcludeDockerImages(__FilterDockerImages):
    """
    Exclude Docker images by name and tags.

    You can specify multiple names and tags::

       ExcludePath('*:production*'),
       ExcludePath(['ubuntu:*', 'debian:9']),

    """

    operator = "$nmatch"
    boolean_operator = "$and"


class IncludeFilename(Rule):
    """
    Apply to artifacts by name/mask.

    You can specify multiple paths::

       IncludeFilename('*-*'), # feature-branches
       IncludeFilename(['*tar.gz', '*.nupkg']),

    """

    def __init__(self, mask):
        self.mask = mask

    def _aql_add_filter(self, aql_query_list):
        update_dict = {
            "name": {
                "$match": self.mask,
            }
        }
        aql_query_list.append(update_dict)
        return aql_query_list


class _ExcludeMask(Rule):
    attribute_name = None

    def __init__(
        self,
        masks,
    ):
        if isinstance(masks, str):
            self.masks = [masks]
        elif isinstance(masks, list):
            self.masks = masks
        else:
            raise AttributeError("Mask must by str|list")

    def _aql_add_filter(self, aql_query_list):
        rule_list = []
        for mask in self.masks:
            update_dict = {
                self.attribute_name: {
                    "$nmatch": mask,
                }
            }
            rule_list.append(update_dict)
        and_list = {"$and": rule_list}

        aql_query_list.append(and_list)
        return aql_query_list


class ExcludePath(_ExcludeMask):
    """
    Exclude artifacts by path/mask.

    You can specify multiple paths::

       ExcludePath('*production*'),
       ExcludePath(['*release*', '*master*']),

    """

    attribute_name = "path"


class ExcludeFilename(_ExcludeMask):
    """
    Exclude artifacts by name/mask.

    You can specify multiple paths::

       ExcludeFilename('*-*'), # feature-branch
       ExcludeFilename(['*tar.gz', '*.nupkg']),

    """

    attribute_name = "name"


# under_score - old style of naming
# Keep it for backward compatibility
include_path = IncludePath
include_docker_images = IncludeDockerImages
exclude_docker_images = ExcludeDockerImages
include_filename = IncludeFilename
exclude_path = ExcludePath
exclude_filename = ExcludeFilename
