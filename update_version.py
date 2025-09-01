#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "httpx",
#     "pyyaml",
# ]
# ///
"""Update the version and SHA256 hashes in the pydantic_ai-feedstock recipe.

Example
-------

To update the recipe to version 0.3.4, run:

.. code-block:: console

    uv run update_version.py 0.3.4

"""

import argparse
from dataclasses import dataclass
import httpx
import re
import sys
from pathlib import Path
import yaml


def fetch_sha256_from_pypi(package_name: str, version: str) -> str:
    """Fetch SHA256 hash for a package from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()

        data = response.json()

        # Find the source distribution (tar.gz)
        for release in data["urls"]:
            if release["packagetype"] == "sdist" and release["filename"].endswith(
                ".tar.gz"
            ):
                return release["digests"]["sha256"]

        raise ValueError(f"No source distribution found for {package_name} {version}")


@dataclass
class Package:
    """Data class to represent a package."""

    name: str
    old_sha256: str


def extract_packages_from_recipe(content: str) -> list[Package]:
    """Extract package names from the recipe content."""
    data = yaml.safe_load(content)
    return [
        Package(output["package"]["name"], output["source"][0]["sha256"])
        for output in data.get("outputs", [])
    ]


def update_recipe(recipe_path: Path, new_version: str):
    """Update the recipe file with new version and SHA256 hashes."""
    content = recipe_path.read_text()

    # Update version in context
    content = re.sub(
        r'(context:\s*\n\s*version:\s*")[^"]+(")', rf"\g<1>{new_version}\g<2>", content
    )

    # Extract packages dynamically from the recipe
    packages = extract_packages_from_recipe(content)

    # Update SHA256 hashes for each package
    for package in packages:
        print(f"Fetching SHA256 for {package.name} {new_version}...")
        try:
            new_sha = fetch_sha256_from_pypi(package.name, new_version)

            content = content.replace(package.old_sha256, new_sha)
            print(f"  Updated SHA256 for {package.name}")

        except Exception as e:
            print(f"  Error fetching SHA256 for {package.name}: {e}", file=sys.stderr)
            sys.exit(1)

    # Write the updated content back
    recipe_path.write_text(content)
    print(f"\nSuccessfully updated recipe to version {new_version}")


def main():
    parser = argparse.ArgumentParser(
        description="Update pydantic_ai-feedstock recipe version and SHA256 hashes"
    )
    parser.add_argument("version", help="New version number (e.g., 0.3.4)")
    parser.add_argument(
        "--recipe",
        type=Path,
        default=Path("recipe/recipe.yaml"),
        help="Path to recipe.yaml file (default: recipe/recipe.yaml)",
    )

    args = parser.parse_args()

    if not args.recipe.exists():
        print(f"Error: Recipe file not found at {args.recipe}", file=sys.stderr)
        sys.exit(1)

    update_recipe(args.recipe, args.version)


if __name__ == "__main__":
    main()
