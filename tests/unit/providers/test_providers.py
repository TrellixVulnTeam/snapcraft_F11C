# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from unittest.mock import patch

import pytest
from craft_providers import bases

from snapcraft.providers import providers


@pytest.fixture()
def mock_default_command_environment():
    with patch(
        "craft_providers.bases.buildd.default_command_environment",
        return_value=dict(PATH="test-path"),
    ) as mock_environment:
        yield mock_environment


@pytest.mark.parametrize(
    "platform, snap_channel, expected_snap_channel",
    [
        ("linux", None, None),
        ("linux", "edge", "edge"),
        ("darwin", "edge", "edge"),
        # default to stable on non-linux system
        ("darwin", None, "stable"),
    ],
)
@pytest.mark.parametrize(
    "alias",
    [
        bases.BuilddBaseAlias.BIONIC,
        bases.BuilddBaseAlias.FOCAL,
        bases.BuilddBaseAlias.JAMMY,
    ],
)
def test_get_base_configuration(
    platform,
    snap_channel,
    expected_snap_channel,
    alias,
    tmp_path,
    mocker,
):
    """Verify the snapcraft snap is installed from the correct channel."""
    mocker.patch("sys.platform", platform)
    mocker.patch(
        "snapcraft.providers.providers.get_managed_environment_snap_channel",
        return_value=snap_channel,
    )
    mocker.patch(
        "snapcraft.providers.providers.get_command_environment",
        return_value="test-env",
    )
    mocker.patch(
        "snapcraft.providers.providers.get_instance_name",
        return_value="test-instance-name",
    )
    mock_buildd_base = mocker.patch(
        "snapcraft.providers.providers.SnapcraftBuilddBaseConfiguration"
    )

    providers.get_base_configuration(
        alias=alias,
        instance_name="test-instance-name",
    )

    mock_buildd_base.assert_called_with(
        alias=alias,
        environment="test-env",
        hostname="test-instance-name",
        snaps=[
            bases.buildd.Snap(
                name="snapcraft", channel=expected_snap_channel, classic=True
            )
        ],
        packages=["gnupg", "dirmngr", "git"],
    )


def test_get_command_environment(mocker, mock_default_command_environment):
    """Verify command environment is properly constructed."""
    command_environment = providers.get_command_environment()

    assert command_environment == {"PATH": "test-path", "SNAPCRAFT_MANAGED_MODE": "1"}


def test_get_command_environment_passthrough(
    mocker, mock_default_command_environment, monkeypatch
):
    """Verify variables from the environment are passed to the command environment."""
    monkeypatch.setenv("http_proxy", "test-http")
    monkeypatch.setenv("https_proxy", "test-https")
    monkeypatch.setenv("no_proxy", "test-no-proxy")
    monkeypatch.setenv("SNAPCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS", "test-extensions")
    monkeypatch.setenv("SNAPCRAFT_BUILD_FOR", "test-build-for")
    monkeypatch.setenv("SNAPCRAFT_BUILD_INFO", "test-build-info")
    monkeypatch.setenv("SNAPCRAFT_IMAGE_INFO", "test-image-info")

    # ensure other variables are not being passed
    monkeypatch.setenv("other_var", "test-other-var")

    command_environment = providers.get_command_environment()

    assert command_environment == {
        "PATH": "test-path",
        "SNAPCRAFT_MANAGED_MODE": "1",
        "http_proxy": "test-http",
        "https_proxy": "test-https",
        "no_proxy": "test-no-proxy",
        "SNAPCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS": "test-extensions",
        "SNAPCRAFT_BUILD_FOR": "test-build-for",
        "SNAPCRAFT_BUILD_INFO": "test-build-info",
        "SNAPCRAFT_IMAGE_INFO": "test-image-info",
    }


def test_get_command_environment_http_https_proxy(
    mocker, mock_default_command_environment
):
    """Verify http and https proxies are added to the environment."""
    command_environment = providers.get_command_environment(
        http_proxy="test-http", https_proxy="test-https"
    )

    assert command_environment == {
        "PATH": "test-path",
        "SNAPCRAFT_MANAGED_MODE": "1",
        "http_proxy": "test-http",
        "https_proxy": "test-https",
    }


def test_get_command_environment_http_https_priority(
    mocker, mock_default_command_environment, monkeypatch
):
    """Verify http and https proxies from the function argument take priority over the
    proxies defined in the environment."""
    monkeypatch.setenv("http_proxy", "test-http-from-env")
    monkeypatch.setenv("https_proxy", "test-https-from-env")

    command_environment = providers.get_command_environment(
        http_proxy="test-http-from-arg", https_proxy="test-https-from-arg"
    )

    assert command_environment == {
        "PATH": "test-path",
        "SNAPCRAFT_MANAGED_MODE": "1",
        "http_proxy": "test-http-from-arg",
        "https_proxy": "test-https-from-arg",
    }


def test_get_instance_name(new_dir):
    """Test formatting of instance name."""
    inode_number = str(new_dir.stat().st_ino)
    expected_name = f"snapcraft-hello-world-on-arm64-for-armhf-{inode_number}"
    actual_name = providers.get_instance_name(
        project_name="hello-world",
        project_path=new_dir,
        build_on="arm64",
        build_for="armhf",
    )
    assert expected_name == actual_name