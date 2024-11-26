from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Union

from treelib import Node, Tree

from artifactory_cleanup.rules.base import ArtifactDict, ArtifactsList


def is_repository(data):
    return data["path"] == "." and data["name"] == "."


def get_fullpath(repo, path, name, **kwargs):
    """
    Get path from raw Artifactory's data
    """
    if name == ".":
        # root - repository itself
        return repo
    if path == ".":
        # folder under the root
        return f"{repo}/{name}"
    # Usual folder or a file
    return f"{repo}/{path}/{name}"


def split_fullpath(fullpath: str) -> Tuple[str, Optional[str]]:
    """
    Split path into (name, parent)
    >>> split_fullpath("repo/folder/filename.py")
    ('filename.py', 'repo/folder')

    >>> split_fullpath("repo")
    ('repo', None)
    """
    parts = fullpath.rsplit("/", maxsplit=1)
    if len(parts) == 1:
        return parts[0], None
    return parts[1], parts[0]


def parse_fullpath(fullpath: str) -> Tuple[str, str, str]:
    """
    Parse full path to (repo, path, name)
    >>> parse_fullpath("repo/path/name.py")
    ('repo', 'path', 'name.py')

    >>> parse_fullpath("repo/path")
    ('repo', '.', 'path')

    >>> parse_fullpath("repo")
    ('repo', '.', '.')
    """
    if "/" not in fullpath:
        # root - repository itself
        return fullpath, ".", "."
    name, repo_path = split_fullpath(fullpath)

    if "/" not in repo_path:
        # folder under the root
        return repo_path, ".", name

    # Usual folder or a file
    repo, path = repo_path.split("/", maxsplit=1)
    return repo, path, name


class ArtifactNode(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files = 0

    def is_file(self):
        if not self.data:
            return False
        return self.data["type"] == "file"

    def get_raw_data(self) -> Dict:
        """
        Get Artifactory raw data.

        If we don't know exactly data - we try to build it from what we know
        """
        if self.data:
            return self.data

        repo, path, name = parse_fullpath(self.identifier)
        data = dict(repo=repo, path=path, name=name)
        return data


class RepositoryTree(Tree):
    def parse_artifact(self, data):
        """
        Parse Artifactory's raw data and add artifact to the tree
        """
        fullpath = get_fullpath(**data)
        self.add_artifact(fullpath, data)

    def add_artifact(self, fullpath, data):
        existed = self.get_node(fullpath)
        if existed and existed.data is None:
            # We met it before, but with no data
            existed.data = data
            return existed

        name, parent = split_fullpath(fullpath)
        self.upsert_path(parent)
        artifact = ArtifactNode(tag=name, identifier=fullpath, data=data)
        self.add_node(node=artifact, parent=parent)
        return artifact

    def upsert_path(self, fullpath):
        """
        Create path to the folder if not exist
        """
        if not fullpath:
            return

        exists = self.contains(fullpath)
        if exists:
            return

        self.add_artifact(fullpath, data=None)

    def count_files(self, nid=None) -> int:
        """Count files inside the directory. DFS traversing"""
        nid = nid or self.root
        node: ArtifactNode = self.get_node(nid)
        if node.is_file():
            node.files = 1
            return node.files

        children: List[ArtifactNode] = self.children(nid)
        for child in children:
            self.count_files(child.identifier)
        files = sum(child.files for child in children)
        node.files = files
        return node.files

    def get_highest_empty_folders(self, nid=None) -> List[ArtifactNode]:
        """Get the highest empty folders for the repository. DFS traversing"""
        nid = nid or self.root
        node: ArtifactNode = self.get_node(nid)
        if not node.is_root() and node.files == 0:
            # Empty folder that contains only empty folders
            if all(child.files == 0 for child in self.children(nid)):
                return [node]

        folders = []
        for child in self.children(nid):
            _folder = self.get_highest_empty_folders(nid=child.identifier)
            folders.extend(_folder)
        return folders


def build_repositories(artifacts: List[Dict]) -> List[RepositoryTree]:
    """Build tree-like repository objects from raw Artifactory data"""
    repositories = defaultdict(RepositoryTree)
    for data in artifacts:
        repo = repositories[data["repo"]]
        repo.parse_artifact(data)
    return list(repositories.values())


def get_empty_folders(repositories: List[RepositoryTree]) -> ArtifactsList:
    folders = []
    for repo in repositories:
        repo.count_files()
    for repo in repositories:
        _folders = repo.get_highest_empty_folders()
        folders.extend(_folders)

    # Convert to raw data, similar to JSON Artifactory response
    artifacts = ArtifactsList(folder.get_raw_data() for folder in folders)
    for data in artifacts:
        if is_repository(data):
            raise ValueError("Can not remove repository root")

    return artifacts


def to_masks(masks: Union[str, List[str]]):
    """Ensure masks passed as string OR List"""
    if isinstance(masks, str):
        return [masks]
    elif isinstance(masks, list):
        return masks
    else:
        raise AttributeError("'masks' argument must by list of string OR string")


def sort_by_usage(artifact: ArtifactDict) -> str:
    try:
        return artifact["stats"]["downloaded"]
    except:
        return artifact["created"]
