from artifactory_cleanup import CleanupPolicy
from artifactory_cleanup.rules import (
    KeepLatestNVersionImagesByProperty,
    ArtifactsList,
    RuleForDocker,
    DeleteDockerImagesOlderThan,
)


class TestKeepLatestNVersionImagesByProperty:
    def test_filter(self):
        # Skip collecting docker size
        RuleForDocker._collect_docker_size = lambda self, x: x

        data = [
            {
                "properties": {"docker.manifest": "0.1.100"},
                "path": "foobar/0.1.100",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "0.1.200"},
                "path": "foobar/0.1.200",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "0.1.99"},
                "path": "foobar/0.1.99",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "1.1.1"},
                "path": "foobar/1.1.1",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "1.2.1"},
                "path": "foobar/1.2.1",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "1.3.1"},
                "path": "foobar/1.3.1",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "2.1.1"},
                "path": "foobar/2.1.1",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "0.1.86"},
                "path": "baz/0.1.86",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "0.1.87"},
                "path": "baz/0.1.87",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "0.1.83"},
                "path": "baz/0.1.83",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "v0.1.100"},
                "path": "qux/v0.1.100",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "v0.1.200"},
                "path": "qux/v0.1.200",
                "name": "manifest.json",
            },
            {
                "properties": {"docker.manifest": "v0.1.99"},
                "path": "qux/v0.1.99",
                "name": "manifest.json",
            },
        ]
        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy(
            "test",
            # DeleteDockerImagesOlderThan here just to test how KeepLatestNVersionImagesByProperty works together
            DeleteDockerImagesOlderThan(days=1),
            KeepLatestNVersionImagesByProperty(
                count=2,
                number_of_digits_in_version=1,
                custom_regexp=r"(^v?\d+\.\d+\.\d+$)",
            ),
        )
        assert policy.filter(artifacts) == [
            {
                "name": "0.1.83",
                "path": "baz",
                "properties": {"docker.manifest": "0.1.83"},
                "stats": {},
            },
            {
                "name": "0.1.99",
                "path": "foobar",
                "properties": {"docker.manifest": "0.1.99"},
                "stats": {},
            },
            {
                "name": "1.1.1",
                "path": "foobar",
                "properties": {"docker.manifest": "1.1.1"},
                "stats": {},
            },
            {
                "name" : "v0.1.99",
                "path": "qux",
                "properties": {"docker.manifest": "v0.1.99"},
                "stats": {},
            },
        ]
