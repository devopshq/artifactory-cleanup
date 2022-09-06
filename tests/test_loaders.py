from artifactory_cleanup import YamlConfigLoader


class TestYamlLoader:
    def test_all_rules(self, shared_datadir):
        loader = YamlConfigLoader(shared_datadir / "all-built-in-rules.yaml")
        policies = loader.get_policies()
        assert len(policies) == 6, "5 rules files + 1 special for repo-without-name"
