"""Iskrov Agent package root.

This package hosts the cloud-local controller, policy, tools, evidence and
recovery runtime. It implements the Progressive Reasoning Protocol strategy.
"""

__all__ = ["__version__", "PACKAGE_NAME", "LICENSE_EXPRESSION", "package_info"]

__version__ = "0.0.1"

PACKAGE_NAME = "iskrov-agent"

LICENSE_EXPRESSION = "AGPL-3.0-only"


def package_info() -> dict[str, str]:
    """Return the package identity as a plain mapping."""
    return {
        "name": PACKAGE_NAME,
        "version": __version__,
        "license": LICENSE_EXPRESSION,
    }
