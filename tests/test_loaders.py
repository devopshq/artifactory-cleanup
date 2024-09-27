from artifactory_cleanup.loaders import YamlConfigLoader


class TestYamlLoader:
    def test_all_rules(self, shared_datadir):
        loader = YamlConfigLoader(shared_datadir / "all-built-in-rules.yaml")
        policies = loader.get_policies()
        assert len(policies) == 6, "5 rules files + 1 special for repo-without-name"

    def test_load_env_variables(self, shared_datadir, monkeypatch):
        monkeypatch.setenv("ARTIFACTORY_USERNAME", "UserName")
        monkeypatch.setenv("ARTIFACTORY_PASSWORD", "P@ssw0rd")
        monkeypatch.setenv("ARTIFACTORY_APIKEY", "Ap1Key")

        loader = YamlConfigLoader(shared_datadir / "all-built-in-rules.yaml")
        server, user, password, apikey = loader.get_connection()

        assert server == "https://repo.example.com/artifactory"
        assert user == "UserName"
        assert password == "P@ssw0rd"
        assert apikey == "Ap1Key"
