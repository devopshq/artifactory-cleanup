from artifactory_cleanup.rules.base import symbols_to_nuget, parse_cross, parse_cross_any_extenstion
from artifactory_cleanup.rules.base import CrossPackage


def test_symbols_to_nuget_regexp():
    assert symbols_to_nuget("package.package1.11.0.19226.symbols.tar.gz") == (
        "package.package1",
        "11.0.19226",
    )
    assert symbols_to_nuget("package2.11.012341.symbols.tar.gz") == (
        "package2",
        "11.012341",
    )
    assert symbols_to_nuget(
        "package.package1.package2.11.0.1234.1234.symbols.tar.gz"
    ) == ("package.package1.package2", "11.0.1234.1234")
    assert "package.package1", "11.0.19226-feature" == symbols_to_nuget(
        "package.package1.11.0.19226-feature.symbols.tar.gz"
    )
    assert symbols_to_nuget("package.1.11.0.19226.nosymbols.tar.gz") == (None, None)
    assert symbols_to_nuget("package.1.11.0.19226.symbolS.tar.gz") == (None, None)
    assert symbols_to_nuget("package.1.11.0.19226-feature.symbolS.tar.gz") == (
        None,
        None,
    )


def test_parse_cross():
    assert parse_cross(
        "name/branch/1.2.1234/os/compiler/arch/name.1.2.1234.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.1234")
    assert parse_cross(
        "name/branch/1.2.1234/os/compiler/arch/name.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.1234")
    assert parse_cross(
        "name/branch/1.2.3.1234/os/compiler/arch/name.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.3.1234")
    assert parse_cross(
        "na-m4e/1.2-pm/1.2.3.1234/os/compiler/arch/na-m4e.1.2.3.1234.tar.gz"
    ) == CrossPackage("na-m4e", "1.2-pm", "1.2.3.1234")
    assert parse_cross(
        "name/branch/1.2.123/os/compiler/arch/name-1.2.123.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.123")
    assert (
        parse_cross("name/branch/1.2.123/os/compiler/arch/name.1.2.123.nupkg") is None
    )
    assert (
        parse_cross("name/branch/1.2.123/os/compiler/arch/name.1.2.456.tar.gz") is None
    )
    assert (
        parse_cross("name/branch/1.2.123/os/compiler/arch/name-feature.1.2.123.tar.gz")
        is None
    )


def test_parse_cross_any_extenstion():
    assert parse_cross_any_extenstion(
        "name/branch/1.2.1234/os/compiler/arch/name.1.2.1234.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.1234")

    assert parse_cross_any_extenstion(
        "name/branch/1.2.1234/os/compiler/arch/name.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.1234")

    assert parse_cross_any_extenstion(
        "name/branch/1.2.3.1234/os/compiler/arch/name.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.3.1234")

    assert parse_cross_any_extenstion(
        "na-m4e/1.2-pm/1.2.3.1234/os/compiler/arch/na-m4e.1.2.3.1234.tar.gz"
    ) == CrossPackage("na-m4e", "1.2-pm", "1.2.3.1234")

    assert parse_cross_any_extenstion(
        "name/branch/1.2.123/os/compiler/arch/name-1.2.123.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.123")

    assert parse_cross_any_extenstion(
        "name/branch/1.2.123/os/compiler/arch/name.1.2.123.nupkg"
    ) == CrossPackage("name", "branch", "1.2.123")

    assert parse_cross_any_extenstion(
        "name/branch/1.2.123/os/compiler/arch/name.1.2.456.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.123")

    assert parse_cross_any_extenstion(
        "name/branch/1.2.123/os/compiler/arch/name-feature.1.2.123.tar.gz"
    ) == CrossPackage("name", "branch", "1.2.123")
