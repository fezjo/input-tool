#!/usr/bin/env python3
# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
# Script that checks if newer github release is available
import requests
from importlib.metadata import version

from input_tool.common.messages import warning

REPO_OWNER = "fezjo"
REPO_NAME = "input-tool"
GITHUB_API_URL_TEMPLATE = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
)
GITHUB_RELEASES_URL_TEMPLATE = (
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest"
)
PIP_UPDATE_TEMPLATE = (
    f"pip install -U git+https://github.com/{REPO_OWNER}/{REPO_NAME}.git"
)


def check_for_updates():
    try:
        current_version = version("input_tool")

        # Send a GET request to the GitHub API
        response = requests.get(GITHUB_API_URL_TEMPLATE.format(REPO_OWNER, REPO_NAME))
        response.raise_for_status()
        latest_version = response.json()["tag_name"].lstrip("v")

        # Compare the versions
        if latest_version != current_version:
            pip_command = PIP_UPDATE_TEMPLATE.format(REPO_OWNER, REPO_NAME)
            releases_url = GITHUB_RELEASES_URL_TEMPLATE.format(REPO_OWNER, REPO_NAME)
            warning(
                f"Newer version {latest_version} is available. "
                f"You are currently using {current_version}."
            )
            warning(f"You can upgrade by running: `{pip_command}`")
            warning(f"or by downloading the latest version from {releases_url}")
    except Exception as e:
        warning(f"Could not check for updates! An error occurred: {e}")


if __name__ == "__main__":
    check_for_updates()
