from artifactory_cleanup import rules
import custom_rules
from policy import RULES


def test_repo_rules():
    for repo_rules in RULES:
        assert isinstance(repo_rules.name, str)


def test_keep_latest_n_version():
    rule = rules.keep_latest_nupkg_n_version(2)

    result = [
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.108",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.113",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.109-Feature",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110-Feature",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.111-Feature",
            },
        },
    ]

    result_expexted = [
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.108",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.109-Feature",
            },
        },
    ]
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_keep_latest_n_version_with_tar_gz():
    rule = rules.keep_latest_nupkg_n_version(1)

    result = [
        {
            "name": ".tar.gz",
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.113",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110-Feature",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.111-Feature",
            },
        },
    ]

    result_expexted = [
        {
            "name": ".tar.gz",
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110-Feature",
            },
        },
    ]
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_keep_latest_n_version_one():
    rule = rules.keep_latest_nupkg_n_version(1)

    result = [
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.113",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110-Feature",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.111-Feature",
            },
        },
    ]

    result_expexted = [
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110-Feature",
            },
        },
    ]
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_keep_latest_n_version_empty():
    rule = rules.keep_latest_nupkg_n_version(2)

    result = [
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.113",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.110-Feature",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.111-Feature",
            },
        },
    ]

    result_expexted = []
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_keep_latest_n_version_patch():
    rule = rules.keep_latest_nupkg_n_version(2)

    result = [
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.2.109-Feature",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.1.111-Feature",
            },
        },
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.1.110-Feature",
            },
        },
    ]

    result_to_delete = [
        {
            "name": ".nupkg",
            "properties": {
                "nuget.id": "Package",
                "nuget.version": "16.0.1.110-Feature",
            },
        },
    ]
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_to_delete


def test_keep_latest_n_file():
    rule = rules.keep_latest_n_file(2)

    result = [
        {"path": 1, "name": 1},
        {"path": 1, "name": 2},
        {"path": 1, "name": 3},
        {"path": 1, "name": 4},
        {"path": 1, "name": 5},
    ]

    result_to_delete = [
        {"path": 1, "name": 1},
        {"path": 1, "name": 2},
        {"path": 1, "name": 3},
    ]
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_to_delete


def test_keep_latest_n_file_empty():
    rule = rules.keep_latest_n_file(10)

    result = [
        {"path": 1, "name": 1},
        {"path": 1, "name": 2},
        {"path": 1, "name": 3},
        {"path": 1, "name": 4},
        {"path": 1, "name": 5},
    ]

    result_to_delete = []
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_to_delete


def test_keep_latest_n_file_in_folder():
    rule = rules.keep_latest_n_file_in_folder(2)

    result = [
        {"path": 1, "name": 1},
        {"path": 1, "name": 2},
        {"path": 1, "name": 3},
        {"path": 1, "name": 4},
        {"path": 1, "name": 5},
        {"path": 2, "name": 1},
        {"path": 2, "name": 2},
        {"path": 2, "name": 3},
        {"path": 2, "name": 4},
        {"path": 2, "name": 5},
        {"path": 3, "name": 1},
        {"path": 3, "name": 2},
        {"path": 3, "name": 3},
    ]

    result_to_delete = [
        {"path": 1, "name": 1},
        {"path": 1, "name": 2},
        {"path": 1, "name": 3},
        {"path": 2, "name": 1},
        {"path": 2, "name": 2},
        {"path": 2, "name": 3},
        {"path": 3, "name": 1},
    ]
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_to_delete


def test_keep_latest_n_file_in_folder_empty():
    rule = rules.keep_latest_n_file_in_folder(100)

    result = [
        {"path": 1, "name": 1},
        {"path": 1, "name": 2},
        {"path": 1, "name": 3},
        {"path": 1, "name": 4},
        {"path": 1, "name": 5},
        {"path": 2, "name": 1},
        {"path": 2, "name": 2},
        {"path": 2, "name": 3},
        {"path": 2, "name": 4},
        {"path": 2, "name": 5},
        {"path": 3, "name": 1},
        {"path": 3, "name": 2},
        {"path": 3, "name": 3},
    ]

    result_to_delete = []
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_to_delete


def test_keep_latest_version_n_file_in_folder():
    rule = rules.keep_latest_version_n_file_in_folder(1)

    result = [
        {
            "name": "name.1.2.100.tar.gz",
            "path": "repo/folder",
        },
        {
            "name": "name.1.2.200.tar.gz",
            "path": "repo/folder",
        },
        {
            "name": "new_name_1.2.3.101.tar.gz",
            "path": "repo/folder",
        },
        {
            "name": "new_name_1.2.4.100.tar.gz",
            "path": "repo/folder",
        },
    ]

    result_expexted = [
        {
            "name": "name.1.2.100.tar.gz",
            "path": "repo/folder",
        },
        {
            "name": "new_name_1.2.3.101.tar.gz",
            "path": "repo/folder",
        },
    ]
    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_delete_if_image_not_contained_in_properties():
    rule = rules.delete_docker_image_if_not_contained_in_properties(
        "docker-repo", "test_docker."
    )

    result = [
        {"properties": {"test_docker.test1": "tag1"}},
        {"properties": {"test_docker.test2": "tag2"}},
    ]

    result_expexted = {
        "test1": {"tag1": True},
        "test2": {"tag2": True},
    }

    assert rule.get_properties_dict(result) == result_expexted


def test_delete_images_older_than_n_days():
    rule = rules.delete_docker_images_older_than(days=10)
    rule._collect_docker_size = lambda x: x

    result = [
        {"path": "repo/image/tag", "name": "manifest.json"},
        {"path": "repo/image/tag1", "name": "manifest.json"},
        {"path": "repo/image/tag2", "name": "manifest.json"},
    ]

    result_expexted = [
        {"path": "repo/image", "name": "tag"},
        {"path": "repo/image", "name": "tag1"},
        {"path": "repo/image", "name": "tag2"},
    ]

    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_keep_latest_n_file_in_folder_by_version():
    rule = custom_rules.keep_latest_cross_package_n_version(2)

    result = [
        {
            "name": "package-name.0.50.100.tar.gz",
            "path": "package-name/master/0.50.100/other/folder/inside",
        },
        {
            "name": "package-name.0.50.90.tar.gz",
            "path": "package-name/develop/0.50.90/other/folder/inside",
        },
        {
            "name": "package-name.0.50.201.tar.gz",
            "path": "package-name/master/0.50.201/other/folder/inside",
        },
        {
            "name": "package-name.0.50.94.tar.gz",
            "path": "package-name/master/0.50.94/other/folder/inside",
        },
        {
            "name": "package-name.0.51.104.tar.gz",
            "path": "package-name/develop/0.51.104/other/folder/inside",
        },
        {
            "name": "package-name.0.51.105.tar.gz",
            "path": "package-name/release/0.51.105/other/folder/inside",
        },
    ]

    result_expexted = [
        {
            "name": "package-name.0.50.94.tar.gz",
            "path": "package-name/master/0.50.94/other/folder/inside",
        },
    ]

    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_keep_latest_n_file_in_folder_by_version_does_not_suit_check_for_major_minor():
    rule = custom_rules.keep_latest_cross_package_n_version(2)
    # версия артефакта, которая не подходит по количеству цифр не удаляется. В result: 0.50.1.02
    result = [
        {
            "name": "package-name.0.50.100.tar.gz",
            "path": "package-name/master/0.50.100/other/folder/inside",
        },
        {
            "name": "package-name.0.50.101.tar.gz",
            "path": "package-name/develop/0.50.101/other/folder/inside",
        },
        {
            "name": "package-name.0.50.1.02.tar.gz",
            "path": "package-name/master/0.50.1.02/other/folder/inside",
        },
        {
            "name": "package-name.0.50.103.tar.gz",
            "path": "package-name/master/0.50.103/other/folder/inside",
        },
        {
            "name": "package-name.0.50.104.tar.gz",
            "path": "package-name/develop/0.50.104/other/folder/inside",
        },
        {
            "name": "package-name.0.50.105.tar.gz",
            "path": "package-name/master/0.50.105/other/folder/inside",
        },
    ]

    result_expexted = [
        {
            "name": "package-name.0.50.100.tar.gz",
            "path": "package-name/master/0.50.100/other/folder/inside",
        },
    ]

    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_keep_latest_n_file_in_folder_by_version_multiple_versions_in_path():
    rule = custom_rules.keep_latest_cross_package_n_version(1)
    # Если в пути есть несколько версий, то артефакт не удаляем.
    # Скорее всего ветку так назвали или ошибочно в пути появилась версия дважды. В result: /0.50/0.50.103/
    result = [
        {
            "name": "package-name.0.50.100.tar.gz",
            "path": "package-name/master/0.50.100/other/folder/inside",
        },
        {
            "name": "package-name.0.50.101.tar.gz",
            "path": "package-name/develop/0.50.101/other/folder/inside",
        },
        {
            "name": "package-name.0.50.102.tar.gz",
            "path": "package-name/0.50/0.50.102/other/folder/inside",
        },
        {
            "name": "package-name.0.50.103.tar.gz",
            "path": "package-name/0.50/0.50.103/other/folder/inside",
        },
        {
            "name": "package-name.0.50.104.tar.gz",
            "path": "package-name/master/0.50.104/other/folder/inside",
        },
    ]

    result_expexted = [
        {
            "name": "package-name.0.50.100.tar.gz",
            "path": "package-name/master/0.50.100/other/folder/inside",
        },
        {
            "name": "package-name.0.50.102.tar.gz",
            "path": "package-name/0.50/0.50.102/other/folder/inside",
        },
    ]

    result_after_filter = rule.filter_result(result)
    assert result_after_filter == result_expexted


def test_delete_files_that_do_not_exist_in_other_repository():
    rule = custom_rules.delete_files_that_do_not_exist_in_other_repository(
        "other_repository", "property"
    )

    result = [
        {
            "name": "package-name.0.50.100.tar.gz",
            "path": "package-name/master/0.50.100/other/folder/inside",
            "properties": {"property": "95117"},
        },
        {
            "name": "package-name.0.50.101.tar.gz",
            "path": "package-name/master/0.50.101/other/folder/inside",
            "properties": {"property": "95118"},
        },
        {
            "name": "package-name.0.50.102.tar.gz",
            "path": "package-name/master/0.50.102/other/folder/inside",
            "properties": {"property": "95119"},
        },
        {
            "name": "package-name.0.50.103.tar.gz",
            "path": "package-name/master/0.50.103/other/folder/inside",
        },
    ]

    artifacts_in_other_repo = [
        {
            "name": "package-name.0.50.100.tar.gz",
            "path": "package-name/master/0.50.100/other/folder/inside",
            "properties": {"property": "95117"},
        },
        {
            "name": "package-name.0.50.101.tar.gz",
            "path": "package-name/master/0.50.101/other/folder/inside",
            "properties": {"property": "95118"},
        },
        {
            "name": "package-name.0.50.102.tar.gz",
            "path": "package-name/master/0.50.102/other/folder/inside",
        },
    ]

    result_expexted = [
        {
            "name": "package-name.0.50.102.tar.gz",
            "path": "package-name/master/0.50.102/other/folder/inside",
            "properties": {"property": "95119"},
        },
    ]

    result_after_filter = rule.remove_artifacts_from_result_artifact_if_property_exists_in_other_repository(
        result, artifacts_in_other_repo
    )
    assert result_after_filter == result_expexted


def test_docker_values():
    rule = rules.delete_docker_image_if_not_contained_in_properties_value(
        "docker-repo", "test_docker."
    )

    result = [
        {"properties": {"test_docker.test1": "value1"}},
        {"properties": {"test_docker.test2": "value2"}},
        {"properties": {"no_test_docker.test3": "value3"}},
        {"no_properties": {"test_key4": "value4"}},
    ]

    expected_set = {"value1", "value2"}

    test_set = rule.get_properties_values(result)

    assert test_set == expected_set
