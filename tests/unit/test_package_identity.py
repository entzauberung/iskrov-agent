"""Package identity for Iskrov Agent v0.1.2."""

import tomllib
from pathlib import Path

import prp_runtime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_VERSION = "0.1.2"
EXPECTED_LICENSE = "AGPL-3.0-only"


def test_package_info_and_project_metadata_agree_on_004() -> None:
    assert prp_runtime.__version__ == EXPECTED_VERSION
    assert prp_runtime.package_info() == {
        "name": "iskrov-agent",
        "version": EXPECTED_VERSION,
        "license": EXPECTED_LICENSE,
    }
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["name"] == "iskrov-agent"
    assert project["version"] == EXPECTED_VERSION
    assert project["license"] == EXPECTED_LICENSE
