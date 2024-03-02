#!/usr/bin/env python3
# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
# Script that checks if newer github release is available
from importlib.metadata import version

import requests

from input_tool.common.messages import Color, default_logger, info, warning

REPO_OWNER = "fezjo"
REPO_NAME = "input-tool"
GITHUB_API_URL_TEMPLATE = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
)
GITHUB_HOME_URL_TEMPLATE = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
PIPX_UPDATE_COMMAND = f"pipx upgrade {REPO_NAME}"
PIP_UPDATE_COMMAND = f"pip install -U --break-system-packages {REPO_NAME}"


def check_for_updates() -> None:
    try:
        current_version = version("input_tool")

        # Send a GET request to the GitHub API
        version_url = GITHUB_API_URL_TEMPLATE.format(REPO_OWNER, REPO_NAME)
        response = requests.get(version_url, timeout=2)
        response.raise_for_status()
        latest_version = response.json()["tag_name"].lstrip("v")

        # Compare the versions
        if latest_version != current_version:
            home_url = GITHUB_HOME_URL_TEMPLATE.format(REPO_OWNER, REPO_NAME)
            effect, noeffect = Color("underlined"), Color("nounderlined")
            warning(
                f"Current `input-tool` version {current_version} is different from\n"
                f"the latest available version {latest_version}. "
                f"You can upgrade by running\n"
                f"{effect}{PIPX_UPDATE_COMMAND}{noeffect}\n"
                "or by running\n"
                f"{effect}{PIP_UPDATE_COMMAND}{noeffect}\n"
                f"or find more information at\n"
                f"{effect}{home_url}{noeffect}"
            )
    except Exception as e:
        warning(f"Could not check for updates! An error occurred:\n{e!r}")


def main():
    check_for_updates()
    info(str(default_logger.statistics))


if __name__ == "__main__":
    main()
