import re
from collections import defaultdict
from datetime import timedelta
from typing import Tuple

import pydash
from artifactory import ArtifactoryPath
from artifactory_cleanup.context_managers import get_context_managers
from artifactory_cleanup.rules import Rule
from artifactory_cleanup.rules.base import ArtifactsList
from artifactory_cleanup.rules.utils import to_masks

ctx_mgr_block, ctx_mgr_test = get_context_managers()


class RuleForDocker(Rule):
    """
    Parent class for Docker rules
    """

    MANIFEST_FILENAME = "manifest.json"

    def get_docker_images_list(self, docker_repo):
        url = f"/api/docker/{docker_repo}/v2/_catalog"
        r = self.session.get(url)
        r.raise_for_status()
        content = r.json()

        return content["repositories"]

    def get_docker_tags_list(self, docker_repo, docker_image):
        url = f"/api/docker/{docker_repo}/v2/{docker_image}/tags/list"
        r = self.session.get(url)
        r.raise_for_status()
        content = r.json()
        return content["tags"]

    def _manifest_to_docker_images(self, artifacts: ArtifactsList):
        """
        Convert manifest.json path to folder path
        Docker rules get path to MANIFEST_FILENAME file,
        in order to remove the whole image we have to "up" one level
        """
        for artifact in artifacts:
            # already done it or it's just a folder
            if "name" not in artifact or artifact["name"] != self.MANIFEST_FILENAME:
                continue

            artifact["path"], docker_tag = artifact["path"].rsplit("/", 1)
            artifact["name"] = docker_tag
            # We're going to collect docker size later
            if "size" in artifact:
                del artifact["size"]
        return artifacts

    def _collect_docker_size(self, artifacts):
        # skip if already get the size
        sizes_collected = all("size" in artifact for artifact in artifacts)
        if sizes_collected:
            return

        docker_repos = list(set(x["repo"] for x in artifacts))
        if docker_repos:
            aql = ArtifactoryPath(self.session.base_url, session=self.session)
            args = ["items.find", {"$or": [{"repo": repo} for repo in docker_repos]}]
            artifacts_list = aql.aql(*args)

            images_sizes = defaultdict(int)
            for docker_layer in artifacts_list:
                image_key = (docker_layer["repo"], docker_layer["path"])
                images_sizes[image_key] += docker_layer["size"]

            for artifact in artifacts:
                image = f"{artifact['path']}/{artifact['name']}"
                image_key = (artifact["repo"], image)
                artifact["size"] = images_sizes.get(image_key, 0)

    def aql_add_filter(self, filters):
        filters.append({"name": {"$match": self.MANIFEST_FILENAME}})
        return filters

    def filter(self, artifacts):
        """Determines the size of deleted images"""
        artifacts = self._manifest_to_docker_images(artifacts)
        artifacts = super(RuleForDocker, self).filter(artifacts)
        self._collect_docker_size(artifacts)
        return artifacts


class DeleteDockerImagesOlderThan(RuleForDocker):
    """Removes Docker image older than ``days`` days"""

    def __init__(self, *, days: int):
        self.days = timedelta(days=days)

    def aql_add_filter(self, filters):
        older_than_date = self.today - self.days
        older_than_date_txt = older_than_date.isoformat()
        print("Delete docker images older than {}".format(older_than_date_txt))
        filter_ = {"modified": {"$lt": older_than_date_txt}}
        filters.append(filter_)
        return super().aql_add_filter(filters)


class DeleteDockerImagesOlderThanNDaysWithoutDownloads(RuleForDocker):
    """
    Deletes images that are older than n days and have not been downloaded.
    """

    def __init__(self, *, days: int):
        self.days = timedelta(days=days)

    def aql_add_filter(self, filters):
        last_day = self.today - self.days
        filter_ = [
            {"stat.downloads": {"$eq": None}},
            {"stat.remote_downloads": {"$eq": None}},
            {"created": {"$lte": last_day.isoformat()}},
        ]
        filters.extend(filter_)
        return super().aql_add_filter(filters)


class DeleteDockerImagesNotUsed(RuleForDocker):
    """Removes Docker image not downloaded ``days`` days"""

    def __init__(self, *, days: int):
        self.days = timedelta(days=days)

    def aql_add_filter(self, filters):
        last_day = self.today - self.days
        print("Delete docker images not used from {}".format(last_day.isoformat()))
        filter_ = {
            "$or": [
                {
                    "$and": [
                        {"stat.downloaded": {"$lte": last_day.isoformat()}},
                        {"stat.remote_downloaded": {"$lte": last_day.isoformat()}},
                    ]
                },
                {
                    "$and": [
                        {"stat.downloaded": {"$lte": last_day.isoformat()}},
                        {"stat.remote_downloads": {"$eq": None}},
                    ]
                },
                {
                    "$and": [
                        {"stat.downloads": {"$eq": None}},
                        {"stat.remote_downloaded": {"$lte": last_day.isoformat()}},
                    ]
                },
                {
                    "$and": [
                        {"stat.downloads": {"$eq": None}},
                        {"stat.remote_downloads": {"$eq": None}},
                        {"created": {"$lte": last_day.isoformat()}},
                    ]
                },
            ],
        }
        filters.append(filter_)
        return super().aql_add_filter(filters)


class FilterDockerImages(RuleForDocker):
    operator = None
    boolean_operator = None

    def __init__(self, masks):
        if not self.operator:
            raise AttributeError("Attribute 'operator' must be specified")
        if not self.boolean_operator:
            raise AttributeError("Attribute 'boolean_operator' must be specified")

        self.masks = to_masks(masks)

    def get_masks(self):
        # alpine:2.4 => alpine/2.4
        return [mask.replace(":", "/") for mask in self.masks]

    def aql_add_filter(self, filters):
        rule_list = []
        for mask in self.get_masks():
            filter_ = {
                "path": {
                    self.operator: mask,
                }
            }
            rule_list.append(filter_)
        filters.append({self.boolean_operator: rule_list})
        return super().aql_add_filter(filters)


class IncludeDockerImages(FilterDockerImages):
    """
    Apply to docker images with the specified names and tags.
    """

    operator = "$match"
    boolean_operator = "$or"


class ExcludeDockerImages(FilterDockerImages):
    """
    Exclude Docker images by name and tags.
    """

    operator = "$nmatch"
    boolean_operator = "$and"


class KeepLatestNDockerImages(RuleForDocker):
    """
    Leaves ``count`` Docker image digests for each image. This allows tags that have the same digest to be kept.
    """

    def __init__(self, count: int):
        self.count = count

    def filter(self, artifacts):
        artifacts = self._manifest_to_docker_images(artifacts)
        artifacts_by_path = defaultdict(list)

        for artifact in artifacts:
            path = artifact["path"]
            artifacts_by_path[path].append(artifact)

        for path, _artifacts in artifacts_by_path.items():
            sha256s_to_keep = set()
            _artifacts.sort(reverse=True, key=lambda x: x['updated'])
            for artifact in _artifacts:
                if len(sha256s_to_keep) < self.count:
                    sha256s_to_keep.add(artifact['sha256'])
                if artifact['sha256'] in sha256s_to_keep:
                    artifacts.keep(artifact)

        return artifacts

class KeepLatestNVersionImagesByProperty(RuleForDocker):
    r"""
    Leaves ``count`` Docker images with the same major.
    If you need to add minor then put 2 or if patch then put 3.

    :param custom_regexp: how to determine version.
    By default ``r'(^ \d*\.\d*\.\d*.\d+$)``. Find a version in ``properties`` of the file ``manifest.json``
    """

    def __init__(
        self,
        count: int,
        custom_regexp=r"(^\d+\.\d+\.\d+$)",
        number_of_digits_in_version: int = 1,
    ):
        self.count = count
        self.custom_regexp = custom_regexp
        self.property = r"docker.manifest"
        self.number_of_digits_in_version = number_of_digits_in_version

    def get_version(self, artifact) -> Tuple:
        """Parse property and get version from it"""
        value = artifact["properties"][self.property]
        match = re.match(self.custom_regexp, value)
        if not match:
            raise ValueError(f"Can not find version in '{artifact}'")
        version_str = match.group()
        if version_str.startswith("v"):
            version_str = version_str[1:]
            return tuple(["v"] + list(map(int, version_str.split("."))))
        version = tuple(map(int, version_str.split(".")))
        return version


    def filter(self, artifacts):
        artifacts.sort(key=lambda x: x["path"])

        def _groupby(artifact):
            """Group by major/minor/patch version"""
            return (
                artifact["path"],
                self.get_version(artifact)[: self.number_of_digits_in_version],
            )

        # Group artifacts by major/minor or patch
        grouped = pydash.group_by(artifacts, iteratee=_groupby)

        for main_version, artifacts_ in grouped.items():
            artifacts_ = list(artifacts_)
            artifacts_.sort(key=self.get_version, reverse=True)
            # Keep latest N artifacts
            artifacts.keep(artifacts_[: self.count])

        return super().filter(artifacts)


class DeleteDockerImageIfNotContainedInProperties(RuleForDocker):
    """
    Remove Docker image, if it is not found in the properties of the artifact repository.
    """

    def __init__(
        self,
        docker_repo,
        properties_prefix,
        image_prefix=None,
        full_docker_repo_name=None,
    ):
        self.docker_repo = docker_repo
        self.properties_prefix = properties_prefix
        self.image_prefix = image_prefix
        self.full_docker_repo_name = full_docker_repo_name

    def get_properties_dict(self, artifacts):
        properties_dict = defaultdict(dict)

        for artifact in artifacts:
            if artifact.get("properties"):
                properties_with_image = [
                    x
                    for x in artifact["properties"].keys()
                    if x.startswith(self.properties_prefix)
                ]

                for i in properties_with_image:
                    # Create a dictionary with a property key, without a prefix.
                    # Property = docker.image, prefix = docker. -> key = image
                    properties_dict[i[len(self.properties_prefix) :]].setdefault(
                        artifact["properties"][i], True
                    )

        return properties_dict

    def filter(self, artifacts):
        images = self.get_docker_images_list(self.docker_repo)
        properties_dict = self.get_properties_dict(artifacts)
        result_docker_images = []

        for image in images:
            # legacy
            image_legacy = None
            if self.image_prefix and image.startswith(self.image_prefix):
                # Remove the prefix from the image name
                image_legacy = image[len(self.image_prefix) :]
            elif not self.image_prefix:
                continue

            if (
                image in properties_dict.keys()
                or image_legacy in properties_dict.keys()
            ):
                tags = self.get_docker_tags_list(self.docker_repo, image)

                for tag in tags:
                    docker_name = "{}:{}".format(image, tag)
                    docker_name_legacy = None
                    if self.full_docker_repo_name:
                        docker_name_legacy = "{}/{}".format(
                            self.full_docker_repo_name, docker_name
                        )
                    # If this docker tag is not found in the metadata properties, then add it to the list for deletion
                    if (
                        not properties_dict[image].pop(docker_name, None)
                        and not properties_dict[image_legacy].pop(docker_name, None)
                        and not properties_dict[image_legacy].pop(
                            docker_name_legacy, None
                        )
                    ):
                        result_docker_images.append(
                            {
                                "repo": self.docker_repo,
                                "path": image,
                                "name": tag,
                            }
                        )

        return super().filter(artifacts)


class DeleteDockerImageIfNotContainedInPropertiesValue(RuleForDocker):
    """
    Remove Docker image, if it is not found in the properties of the artifact repository
    """

    def __init__(
        self,
        docker_repo,
        properties_prefix,
        image_prefix=None,
        full_docker_repo_name=None,
    ):
        self.docker_repo = docker_repo
        self.properties_prefix = properties_prefix
        self.image_prefix = image_prefix
        self.full_docker_repo_name = full_docker_repo_name

    def get_properties_values(self, artifacts):
        """Creates a list of artifact property values if the value starts with self.properties_prefix"""
        properties_values = set()
        for artifact in artifacts:
            properties_values |= set(
                (
                    artifact["properties"].get(x)
                    for x in artifact.get("properties", {})
                    if x.startswith(self.properties_prefix)
                )
            )

        return properties_values

    def filter(self, artifacts):
        images = self.get_docker_images_list(self.docker_repo)
        properties_values = self.get_properties_values(artifacts)
        result_docker_images = []

        for image in images:
            if not image.startswith(self.image_prefix):
                continue

            # For debug output all properties that begin as image
            values_with_image_name = [
                x for x in properties_values if x.startswith(image)
            ]

            with ctx_mgr_block(f"Values of properties with name as image {image}"):
                for value in values_with_image_name:
                    print(value)

            tags = self.get_docker_tags_list(self.docker_repo, image)

            with ctx_mgr_block(f"Checking image {image}"):
                for tag in tags:
                    docker_name = "{}:{}".format(image, tag)
                    print("INFO - Checking docker with name {}".format(docker_name))
                    # If this Docker tag is not found in the metadata properties, then add it to the list for deletion
                    if docker_name not in properties_values:
                        result_docker_images.append(
                            {
                                "repo": self.docker_repo,
                                "path": image,
                                "name": tag,
                            }
                        )

        return result_docker_images
