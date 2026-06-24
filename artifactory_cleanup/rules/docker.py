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
    FAT_MANIFEST_FILENAME = "list.manifest.json"

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
        Convert manifest.json or list.manifest.json path to folder path
        Docker rules get path to MANIFEST_FILENAME file or FAT_MANIFEST_FILENAME for multiarch images,
        in order to remove the whole image we have to "up" one level
        """
        for artifact in artifacts:
            # already done it or it's just a folder
            if "name" not in artifact or artifact["name"] not in [
                self.MANIFEST_FILENAME,
                self.FAT_MANIFEST_FILENAME,
            ]:
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
        filters.append({'$or': [{'name': {'$match': self.MANIFEST_FILENAME},
                                'repo': {'$ne': None}},
                               {'name': {'$match': self.FAT_MANIFEST_FILENAME},
                                'repo': {'$ne': None}}]})

    def _get_sums_from_manifest(self, artifacts):
        sums = []
        for artifact in artifacts:
            if artifact["name"] == self.FAT_MANIFEST_FILENAME:
                with open(artifact["path"], "r") as f:
                    manifest = json.load(f)
                for image in manifest:
                    sums.append(image["digest"])
        return sums

    def _exclude_sums(self, artifacts, sums):
        excluded_sums = []
        for artifact in artifacts:
            if artifact["name"] == self.FAT_MANIFEST_FILENAME:
                with open(artifact["path"], "r") as f:
                    manifest = json.load(f)
                for image in manifest:
                    if image["digest"] not in sums:
                        excluded_sums.append(image["digest"])
        return excluded_sums

    def _remove_manifest(self, artifacts):
        for artifact in artifacts:
            if artifact["name"] == self.FAT_MANIFEST_FILENAME:
                os.remove(artifact["path"])
                return

    def _select_sha_from_manifest(self, artifacts, sums):
        selected_sha = []
        for artifact in artifacts:
            if artifact["name"] == self.FAT_MANIFEST_FILENAME:
                with open(artifact["path"], "r") as f:
                    manifest = json.load(f)
                for image in manifest:
                    if image["digest"] in sums:
                        selected_sha.append(image["digest"])
        return selected_sha