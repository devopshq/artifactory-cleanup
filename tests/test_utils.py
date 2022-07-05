import json

from artifactory_cleanup.rules.utils import (
    artifacts_list_to_tree,
    folder_artifacts_without_children,
)


def test_artifacts_list_to_tree():
    with open("artifacts_list.json", "r") as fp:
        artifacts_list = json.load(fp)

    artifacts_tree = artifacts_list_to_tree(artifacts_list)

    # Just some rough testing to verify that tree is correctly built
    assert sorted(artifacts_tree.keys()) == sorted(["user1", "user2", "user3"])
    assert sorted(artifacts_tree["user1"]["children"].keys()) == sorted(["package1"])
    assert sorted(artifacts_tree["user2"]["children"].keys()) == sorted(
        ["package2", "package5"]
    )
    assert sorted(
        artifacts_tree["user2"]["children"]["package2"]["children"].keys()
    ) == sorted(["4.2.0", "4.2.1"])
    assert sorted(artifacts_tree["user3"]["children"].keys()) == sorted(["package3"])


def test_folder_artifacts_without_children():
    with open("artifacts_list.json", "r") as fp:
        artifacts_list = json.load(fp)

    artifacts_tree = artifacts_list_to_tree(artifacts_list)

    empty_folders = folder_artifacts_without_children(artifacts_tree)

    assert len(empty_folders) == 3

    expected_empty_folders = [
        # Simple empty folder without children in the list, at a deeper level
        "user2/package2/4.2.1",
        # Simple empty folder without children at a higher level
        "user2/package5",
        # Longer folder structure where all subfolders are empty
        "user3",
    ]

    for empty_folder in empty_folders:
        empty_path = (
            empty_folder["path"] + "/" + empty_folder["name"]
            if len(empty_folder["path"]) > 0
            else empty_folder["name"]
        )

        assert empty_path in expected_empty_folders
