from artifactory_cleanup import CleanupPolicy
from artifactory_cleanup.rules import (
    KeepLatestNDockerImages,
    KeepLatestNVersionImagesByProperty,
    ArtifactsList,
    RuleForDocker,
    DeleteDockerImagesOlderThan,
)


class TestKeepLatestNDockerImages:
    def test_filter(self):
        data = [
            {
                "path": "foobar/latest",
                "sha256": "9908cd35ccb5774c0da1c8bae657c48fe42f865a62fded44043fcfe2a09f3e31",
                "name": "manifest.json",
                "updated": "2021-03-20T13:54:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
            },
            {
                "path": "foobar/2021-03-19T13-53-52.383",
                "sha256": "d26a1bf07bd081a5b389d8402df8fec682267d0b02276768b8a9b2bb6bd149a6",
                "name": "manifest.json",
                "updated": "2021-03-19T13:53:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
            },
            {
                "path": "foobar/sha256__9908cd35ccb5774c0da1c8bae657c48fe42f865a62fded44043fcfe2a09f3e31",
                "sha256": "9908cd35ccb5774c0da1c8bae657c48fe42f865a62fded44043fcfe2a09f3e31",
                "name": "manifest.json",
                "updated": "2021-03-19T13:52:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
            },
            {
                "path": "baz/latest",
                "sha256": "42988e2a52ad999d0038b46a7528f6526e4b9e2093f0bf7522eb61ac316715d3",
                "name": "manifest.json",
                "updated": "2021-03-20T13:54:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
            },
            {
                "path": "qux/0.0.1",
                "sha256": "1fbffb7bb96039fae4a89ddd2cbac16b285fac333bc928d6464665e953828054",
                "name": "manifest.json",
                "updated": "2021-03-20T13:54:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
            },
            {
                "path": "qux/0.0.2",
                "sha256": "46c469dbbff12818441d22aa8fed36869e71f3f9a7ec317d57219744e1688e25",
                "name": "manifest.json",
                "updated": "2021-03-20T13:53:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
            },
        ]   

        artifacts = ArtifactsList.from_response(data)
        policy = CleanupPolicy("test", KeepLatestNDockerImages(count=1))
        assert policy.filter(artifacts) == [
            {
                "path": "foobar",
                "sha256": "d26a1bf07bd081a5b389d8402df8fec682267d0b02276768b8a9b2bb6bd149a6",
                "name": "2021-03-19T13-53-52.383",
                "updated": "2021-03-19T13:53:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
                "stats": {},
            },
            {
                "path": "qux",
                "sha256": "46c469dbbff12818441d22aa8fed36869e71f3f9a7ec317d57219744e1688e25",
                "name": "0.0.2",
                "updated": "2021-03-20T13:53:52.383+02:00",
                "properties": {"docker.manifest": "v0.1.99"},
                "stats": {},
            },
        ]

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
