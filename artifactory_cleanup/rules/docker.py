import re
from collections import defaultdict
from datetime import timedelta

from artifactory import ArtifactoryPath
from artifactory_cleanup.context_managers import get_context_managers
from artifactory_cleanup.rules.base import Rule

ctx_mgr_block, ctx_mgr_test = get_context_managers()


class RuleForDocker(Rule):
    """
    Parent class for Docker rules
    """

    def get_docker_images_list(self, docker_repo):
        _href = "{}/api/docker/{}/v2/_catalog".format(
            self.artifactory_server, docker_repo
        )
        r = self.artifactory_session.get(_href)
        r.raise_for_status()
        content = r.json()

        return content["repositories"]

    def get_docker_tags_list(self, docker_repo, docker_image):
        _href = "{}/api/docker/{}/v2/{}/tags/list".format(
            self.artifactory_server, docker_repo, docker_image
        )
        r = self.artifactory_session.get(_href)
        r.raise_for_status()
        content = r.json()

        return content["tags"]

    def _collect_docker_size(self, new_result):
        docker_repos = list(set(x["repo"] for x in new_result))

        if docker_repos:
            aql = ArtifactoryPath(
                self.artifactory_server, session=self.artifactory_session
            )
            args = ["items.find", {"$or": [{"repo": repo} for repo in docker_repos]}]
            artifacts_list = aql.aql(*args)

            images_dict = defaultdict(int)
            for docker_layer in artifacts_list:
                images_dict[docker_layer["path"]] += docker_layer["size"]

            for artifact in new_result:
                image = f"{artifact['path']}/{artifact['name']}"
                artifact["size"] = images_dict[image]

    def filter_result(self, result_artifacts):
        """Determines the size of deleted images"""
        new_result = super(RuleForDocker, self).filter_result(result_artifacts)
        self._collect_docker_size(new_result)

        return new_result


class DeleteDockerImagesOlderThan(RuleForDocker):
    """Removes Docker image older than ``days`` days"""

    def __init__(self, *, days):
        self.days = timedelta(days=days)

    def _aql_add_filter(self, aql_query_list):
        older_than_date = self.today - self.days
        older_than_date_txt = older_than_date.isoformat()
        print("Delete docker images older than {}".format(older_than_date_txt))
        update_dict = {
            "modified": {
                "$lt": older_than_date_txt,
            },
            "name": {
                "$match": "manifest.json",
            },
        }
        aql_query_list.append(update_dict)
        return aql_query_list

    def _filter_result(self, result_artifact):
        for artifact in result_artifact:
            artifact["path"], docker_tag = artifact["path"].rsplit("/", 1)
            artifact["name"] = docker_tag

        return result_artifact


class DeleteDockerImagesOlderThanNDaysWithoutDownloads(RuleForDocker):
    """
    Deletes images that are older than n days and have not been downloaded.
    """

    def __init__(self, *, days):
        self.days = timedelta(days=days)

    def _aql_add_filter(self, aql_query_list):
        last_day = self.today - self.days
        update_dict = {
            "name": {
                "$match": "manifest.json",
            },
            "$and": [
                {"stat.downloads": {"$eq": None}},
                {"created": {"$lte": last_day.isoformat()}},
            ],
        }
        aql_query_list.append(update_dict)
        return aql_query_list

    def _filter_result(self, result_artifact):
        for artifact in result_artifact:
            artifact["path"], docker_tag = artifact["path"].rsplit("/", 1)
            artifact["name"] = docker_tag

        return result_artifact


class DeleteDockerImagesNotUsed(RuleForDocker):
    """Removes Docker image not downloaded ``days`` days"""

    def __init__(self, *, days):
        self.days = timedelta(days=days)

    def _aql_add_filter(self, aql_query_list):
        last_day = self.today - self.days
        print("Delete docker images not used from {}".format(last_day.isoformat()))
        update_dict = {
            "name": {
                "$match": "manifest.json",
            },
            "$or": [
                {"stat.downloaded": {"$lte": last_day.isoformat()}},
                {
                    "$and": [
                        {"stat.downloads": {"$eq": None}},
                        {"created": {"$lte": last_day.isoformat()}},
                    ]
                },
            ],
        }
        aql_query_list.append(update_dict)
        return aql_query_list

    def _filter_result(self, result_artifact):
        for artifact in result_artifact:
            artifact["path"], docker_tag = artifact["path"].rsplit("/", 1)
            artifact["name"] = docker_tag

        return result_artifact


class KeepLatestNVersionImagesByProperty(Rule):
    r"""
    Leaves ``count`` Docker images with the same major.
    If you need to add minor then put 2 or if patch then put 3.

    :param custom_regexp: how to determine version.
    By default ``r'(^ \d*\.\d*\.\d*.\d+$)``. Find a version in ``properties`` of the file ``manifest.json``
    """

    def __init__(
        self,
        count,
        custom_regexp=r"(^\d*\.\d*\.\d*.\d+$)",
        number_of_digits_in_version=1,
    ):
        self.count = count
        self.custom_regexp = custom_regexp
        self.property = r"docker.manifest"
        self.number_of_digits_in_version = number_of_digits_in_version

    def _filter_result(self, result_artifact):
        artifacts_by_path_and_name = defaultdict(list)
        for artifact in result_artifact[:]:
            property = artifact["properties"][self.property]
            version = re.findall(self.custom_regexp, property)
            if len(version) == 1:
                version_splitted = version[0].split(".")
                key = artifact["path"] + "/" + version_splitted[0]
                key += ".".join(version_splitted[: self.number_of_digits_in_version])
                artifacts_by_path_and_name[key].append([version_splitted[0], artifact])

        for artifactory_with_version in artifacts_by_path_and_name.values():
            artifactory_with_version.sort(
                key=lambda x: [int(x) for x in x[0].split(".")]
            )

            good_artifact_count = len(artifactory_with_version) - self.count
            if good_artifact_count < 0:
                good_artifact_count = 0

            good_artifacts = artifactory_with_version[good_artifact_count:]
            for artifact in good_artifacts:
                self.remove_artifact(artifact[1], result_artifact)

        return result_artifact


class KeepLatestNDockerTags(Rule):
    """
    Leaves then most recent ``count`` tags of each Docker image.
    Uses the property "modified" of the manifest.json file to determine the age of the tag.
    """

    def __init__(self, count):
        self.count = count
        self.manifest_file = "manifest.json"
        self.must_have_property = "docker.manifest"

    def _aql_add_filter(self, aql_query_list):
        update_dict = {
            "name": {
                "$eq": self.manifest_file,
            }
        }
        aql_query_list.append(update_dict)
        return aql_query_list

    def _filter_result(self, result_artifact):
        artifacts_by_path = defaultdict(list)

        # Groups the artifacts by image name (ie the path without the tag)
        for artifact in result_artifact[:]:
            if (
                artifact["name"] != self.manifest_file
                or self.must_have_property not in artifact["properties"]
            ):
                # Makes sure we're dealing with a Docker manifest to prevent wrong deletions
                raise Exception(
                    "Wrong filter applied: we're looking for '{}' "
                    "files with the property '{}'".format(
                        self.manifest_file, self.must_have_property
                    )
                )

            path_parts = artifact["path"].split("/")
            if len(path_parts) < 2:
                print(
                    "Manifest {path}/{name} doesn't belong to an image tag, skipping.".format(
                        **artifact
                    )
                )
                continue

            # The folder where the manifest.json resides is to be deleted.
            # To accomplish that, this modifies every artifact so that it points to its parent folder.
            # Also, removes unneeded attributes to prevent mismatching with the modified ones.
            # Size is set to zero because actual size of deleted image is unknown (usually layer files are shared
            # among other images or tags, so the actual space freed cannot be determined without added complexity).
            path = "/".join(path_parts[:-1])
            tag = path_parts[-1]
            artifact = {
                "repo": artifact["repo"],
                "path": path,
                "name": tag,
                "modified": artifact["modified"],
                "size": 0,
            }

            artifacts_by_path[path].append(artifact)

        filtered_artifacts = []
        for path in artifacts_by_path.keys():
            # Sort the tags by modification date of their manifest
            artifacts_by_path[path].sort(key=lambda x: x["modified"])
            limit = len(artifacts_by_path[path]) - self.count
            if limit > 0:
                # Crops the ordered list of tags to the defined count
                filtered_artifacts.extend(artifacts_by_path[path][0:limit])

        return filtered_artifacts


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

    def get_properties_dict(self, result_artifact):
        properties_dict = defaultdict(dict)

        for artifact in result_artifact:
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

    def _filter_result(self, result_artifact):
        images = self.get_docker_images_list(self.docker_repo)
        properties_dict = self.get_properties_dict(result_artifact)
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

        return result_docker_images


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

    def get_properties_values(self, result_artifact):
        """Creates a list of artifact property values if the value starts with self.properties_prefix"""
        properties_values = set()
        for artifact in result_artifact:
            properties_values |= set(
                (
                    artifact["properties"].get(x)
                    for x in artifact.get("properties", {})
                    if x.startswith(self.properties_prefix)
                )
            )

        return properties_values

    def _filter_result(self, result_artifact):
        images = self.get_docker_images_list(self.docker_repo)
        properties_values = self.get_properties_values(result_artifact)
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


# under_score - old style of naming
# Keep it for backward compatibility
delete_docker_images_older_than = DeleteDockerImagesOlderThan
delete_docker_images_older_than_n_days_without_downloads = (
    DeleteDockerImagesOlderThanNDaysWithoutDownloads
)
delete_docker_images_not_used = DeleteDockerImagesNotUsed
keep_latest_n_version_images_by_property = KeepLatestNVersionImagesByProperty
delete_docker_image_if_not_contained_in_properties = (
    DeleteDockerImageIfNotContainedInProperties
)
delete_docker_image_if_not_contained_in_properties_value = (
    DeleteDockerImageIfNotContainedInPropertiesValue
)
