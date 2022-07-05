from collections import defaultdict, deque
from typing import Dict, List


def artifacts_list_to_tree(list_of_artifacts: List):
    """
    Convert a list of artifacts to a dict representing the directory tree.
    Each entry name corresponds to the folder or file name. And has two subnodes 'children' and
    'data'. 'children' is recursively again the list of files/folder within that folder.
    'data' contains the artifact data returned by artifactory.

    Major idea based on https://stackoverflow.com/a/58917078
    """

    def nested_dict():
        """
        Creates a default dictionary where each value is another default dictionary.
        """
        return defaultdict(nested_dict)

    def default_to_regular(d):
        """
        Converts defaultdicts of defaultdicts to dict of dicts.
        """
        if isinstance(d, defaultdict):
            d = {k: default_to_regular(v) for k, v in d.items()}
        return d

    new_path_dict = nested_dict()
    for artifact in list_of_artifacts:
        parts = artifact["path"].split("/")
        if parts:
            marcher = new_path_dict
            for key in parts:
                # We need the repo for the root level folders. They are not in the
                # artifacts list
                marcher[key]["data"] = {"repo": artifact["repo"]}
                marcher = marcher[key]["children"]
            marcher[artifact["name"]]["data"] = artifact
    artifact_tree = default_to_regular(new_path_dict)
    # Artifactory also returns the directory itself. We need to remove it from the list
    # since that tree branch has no children assigned
    if "." in artifact_tree:
        del artifact_tree["."]
    return artifact_tree


def folder_artifacts_without_children(artifacts_tree: Dict, path=""):
    """
    Takes the artifacts tree and returns the list of artifacts which are folders
    and do not have any children.

    If folder1 has only folder2 as a child, and folder2 is empty, the list only contains
    folder1. I.e., empty folders are also recursively propagated back.

    The input tree will be modified and empty folders will be deleted from the tree.

    """

    # use a deque instead of a list. it's faster to add elements there
    empty_folder_artifacts = deque()

    def _add_to_del_list(name: str):
        """
        Add element with name to empty folder list and remove it from the tree
        """
        empty_folder_artifacts.append(artifacts_tree[name]["data"])
        # Also delete the item from the children list to recursively delete folders
        # upwards
        del artifacts_tree[name]

    # Use list(item.keys()) here so that we can delete items while iterating over the
    # dict.
    for artifact_name in list(artifacts_tree.keys()):
        tree_entry = artifacts_tree[artifact_name]
        if "type" in tree_entry["data"] and tree_entry["data"]["type"] == "file":
            continue
        if not "path" in tree_entry["data"]:
            # Set the path and name for root folders which were not explicitly in the
            # artifacts list
            tree_entry["data"]["path"] = path
            tree_entry["data"]["name"] = artifact_name
        if not "children" in tree_entry or len(tree_entry["children"]) == 0:
            # This an empty folder
            _add_to_del_list(artifact_name)
        else:
            artifacts = folder_artifacts_without_children(
                tree_entry["children"],
                path=path + "/" + artifact_name if len(path) > 0 else artifact_name,
            )
            # Additional check needed here because the recursive call may
            # delete additional children.
            # And here we want to check again if all children would be deleted.
            # Then also delete this.
            if len(tree_entry["children"]) == 0:
                # just delete the whole folder since all children are empty
                _add_to_del_list(artifact_name)
            else:
                # add all empty folder children to the list
                empty_folder_artifacts.extend(artifacts)

    return empty_folder_artifacts
