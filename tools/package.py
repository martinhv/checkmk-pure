#!/usr/bin/env python
import os
import subprocess
import sys
from pathlib import Path

author = "Pure Storage"
title = "Pure Storage"
description = "Plugin for Pure Storage FlashArray and FlashBlade devices. Please install the py-pure-client package in your site before using."
download_url = "https://github.com/mkarg75/checkmk-purestorage"

_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

checkmk_lib_path = os.path.abspath(
    os.path.join(_root_path, "src/local/lib/python3")
)
if checkmk_lib_path not in sys.path:
    sys.path.insert(
        0,
        checkmk_lib_path
    )

checkmk_path = os.path.abspath(
    os.path.join(_root_path, "checkmk")
)
if checkmk_path not in sys.path:
    sys.path.insert(
        0,
        checkmk_path
    )


def package_purestorage_mpk():
    from cmk.utils import paths
    from cmk.utils import version as cmk_version
    from cmk.utils.packaging import Manifest, PackagePart, PackageName, Installer, get_unpackaged_files, PathConfig

    local_root = Path(_root_path, "src", "local")
    lib_dir = Path(local_root, "lib")
    agent_based_plugins_dir = Path(lib_dir, "check_mk", "base", "plugins", "agent_based")
    checks_dir = Path(local_root, "share", "check_mk", "checks")
    inventory_dir = Path(local_root, "share", "check_mk", "inventory")
    check_manpages_dir = Path(local_root, "share", "check_mk", "checkman")
    agents_dir = Path(local_root, "share", "check_mk", "agents")
    notifications_dir = Path(local_root, "share", "check_mk", "notifications")
    gui_plugins_dir = Path(lib_dir, "check_mk", "gui", "plugins")
    web_dir = Path(local_root, "share", "check_mk", "web")
    pnp_templates_dir = Path(local_root, "share", "check_mk", "pnp-templates")
    doc_dir = Path(local_root, "share", "doc", "check_mk")
    locale_dir = Path(local_root, "share", "check_mk", "locale")
    bin_dir = Path(local_root, "bin")
    mib_dir = Path(local_root, "share", "snmp", "mibs")
    alert_handlers_dir = Path(local_root, "share", "check_mk", "alert_handlers")
    mkp_rule_pack_dir = Path(_root_path, "build", "ec_rule_packs")
    paths.installed_packages_dir = Path(_root_path, "build", "packages")
    os.makedirs(paths.installed_packages_dir, 0o777, True)
    paths.tmp_dir = Path(_root_path, "build")

    path_config = PathConfig(
        local_root=local_root,
        mkp_rule_pack_dir=mkp_rule_pack_dir,
        agent_based_plugins_dir=agent_based_plugins_dir,
        checks_dir=checks_dir,
        inventory_dir=inventory_dir,
        check_manpages_dir=check_manpages_dir,
        agents_dir=agents_dir,
        notifications_dir=notifications_dir,
        gui_plugins_dir=gui_plugins_dir,
        web_dir=web_dir,
        pnp_templates_dir=pnp_templates_dir,
        doc_dir=doc_dir,
        locale_dir=locale_dir,
        bin_dir=bin_dir,
        lib_dir=lib_dir,
        mib_dir=mib_dir,
        alert_handlers_dir=alert_handlers_dir,
    )

    packagename = "purestorage"

    installer = Installer(paths.installed_packages_dir)

    unpackaged = get_unpackaged_files(installer, path_config)

    # noinspection PyBroadException
    try:
        version = subprocess.check_output(['git', 'describe', '--tags']).decode('ascii').strip()
    except Exception:
        version = '0.0.0'

    from cmk.utils.packaging import PackageVersion
    new_manifest = Manifest(
        title=PackageName(packagename),
        name=PackageName(packagename),
        description=description,
        version=PackageVersion(version),
        version_packaged=cmk_version.__version__,
        version_min_required=cmk_version.__version__,
        version_usable_until=None,
        author=author,
        download_url=download_url,
        files={part: files_ for part in PackagePart if (files_ := unpackaged.get(part))},
    )

    from cmk.utils.packaging import create_mkp_object
    mkp = create_mkp_object(new_manifest, path_config)
    with open(Path(_root_path, "build", "purestorage.mkp"), "wb") as f:
        f.write(mkp)


if __name__ == "__main__":
    package_purestorage_mpk()
