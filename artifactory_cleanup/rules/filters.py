from artifactory_cleanup.rules.base import Rule


class include_path(Rule):
    """
    Apply to artifacts by path / mask.

    You can specify multiple paths::

       include_path('*production*'),
       include_path(['*release*', '*master*']),

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


class __filter_docker_images(Rule):
    operator = None

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

        rule_list = []
        for mask in self.masks:
            if ":" not in mask:
                raise AttributeError("Mask '{}' must contain ':'".format(mask))
            mask = mask.replace(":", "/")  # alpine:2.4 to alpine/2.4
            update_dict = {
                "path": {
                    self.operator: mask,
                }
            }
            rule_list.append(update_dict)

        aql_query_list.append({"$and": rule_list})
        return aql_query_list


class include_docker_images(__filter_docker_images):
    """
    Apply to docker images with the specified names and tags.

    You can specify multiple names and tags::

       include_docker_images('*:production*'),
       include_docker_images(['ubuntu:*', 'debian:9']),

    """

    operator = "$match"


class exclude_docker_images(__filter_docker_images):
    """
    Exclude Docker images by name and tags.

    You can specify multiple names and tags::

       exclude_path('*:production*'),
       exclude_path(['ubuntu:*', 'debian:9']),

    """

    operator = "$nmatch"


class include_filename(Rule):
    """
    Apply to artifacts by name/mask.

    You can specify multiple paths::

       include_filename('*-*'), # фича-ветки
       include_filename(['*tar.gz', '*.nupkg']),

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


class _exclude_mask(Rule):
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


class exclude_path(_exclude_mask):
    """
    Exclude artifacts by path/mask.

    You can specify multiple paths::

       exclude_path('*production*'),
       exclude_path(['*release*', '*master*']),

    """

    attribute_name = "path"


class exclude_filename(_exclude_mask):
    """
    Exclude artifacts by name/mask.

    You can specify multiple paths::

       exclude_filename('*-*'), # фича-ветки
       exclude_filename(['*tar.gz', '*.nupkg']),

    """

    attribute_name = "name"
