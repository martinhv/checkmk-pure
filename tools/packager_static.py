#!/usr/bin/env python
import dataclasses
import gzip
import io
import json
import os
import pathlib
import pprint
import subprocess
import sys
import tarfile
import typing

packagename = "purestorage"
author = "Pure Storage"
title = "Pure Storage"
description = "Plugin for Pure Storage FlashArray and FlashBlade devices. Please install the py-pure-client package in your site before using."
download_url = "https://github.com/mkarg75/checkmk-purestorage"
min_checkmk_version = "2.1.0"

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

_path_map = {
    "agent_based": os.path.join(_root, "src/local/lib/check_mk/base/plugins/agent_based"),
    "checks": os.path.join(_root, "src/local/share/check_mk/checks"),
    "checkman": os.path.join(_root, "src/local/share/check_mk/checkman"),
    "agents": os.path.join(_root, "src/local/share/check_mk/agents"),
    "web": os.path.join(_root, "src/local/share/check_mk/web"),
    "lib": os.path.join(_root, "src/local/lib"),
}

checkmk_path = os.path.abspath(
    os.path.join(_root, "checkmk")
)
if checkmk_path not in sys.path:
    sys.path.insert(
        0,
        checkmk_path
    )
from cmk.utils.version import __version__


@dataclasses.dataclass
class Manifest:
    title: str
    name: str
    description: str
    version: str
    version_packaged: str
    version_min_required: str
    version_usable_until: typing.Optional[str]
    author: str
    download_url: str
    files: typing.Dict[str, typing.List[str]]

    def to_dict(self):
        data = dataclasses.asdict(self)
        data["version.packaged"] = data["version_packaged"]
        del data["version_packaged"]
        data["version.min_required"] = data["version_min_required"]
        del data["version_min_required"]
        data["version.usable_until"] = data["version_usable_until"]
        del data["version_usable_until"]
        return data

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_pprint(self):
        return pprint.pformat(self.to_dict())


def package_directory(path: str, already_packaged_files: typing.List[str]) -> typing.Tuple[
    bytes, typing.List[str]
]:
    """
    Package a single directory into a tar and return it along with the manifest.
    :param path: The path to package.
    :param already_packaged_files: A list of absolute paths to files that should not be packaged.
    :return: A tuple containing the packaged tar as well as a list of new files in the manifest.
    """
    files = pathlib.Path(path).rglob("*")
    filelist = []
    tar = io.BytesIO()
    with tarfile.open(fileobj=tar, mode="w|") as tarhandle:
        for file in files:
            absfile = os.path.abspath(str(file))
            if absfile in already_packaged_files:
                continue
            if not file.is_file():
                continue
            if "__pycache__" in str(file) or ".pyc" in str(file):
                continue
            relfile = os.path.relpath(file, str(path))
            with open(absfile, "rb") as f:
                content = f.read()
                tf = tarfile.TarInfo(relfile)
                tf.size = len(content)
                tarhandle.addfile(tf, io.BytesIO(content))
            filelist.append(relfile)
    tar.seek(0)
    tardata = tar.read()
    return (
        tardata,
        filelist
    )


def package_purestorage_mpk():
    # noinspection PyBroadException
    try:
        version = subprocess.check_output(['git', 'describe', '--tags']).decode('ascii').strip()
    except Exception:
        version = '0.0.0'

    tar = io.BytesIO()
    with tarfile.open(fileobj=tar, mode="w|") as tarhandle:
        packaged_files = []
        manifest_files = {}
        for key, dir in _path_map.items():
            base = os.path.join(_root, dir)
            tarcontents, files = package_directory(path=base, already_packaged_files=packaged_files)
            for file in files:
                packaged_files.append(os.path.join(base, file))
            tf = tarfile.TarInfo(str(key) + ".tar")
            tf.size = len(tarcontents)
            tarhandle.addfile(tf, io.BytesIO(tarcontents))
            manifest_files[key] = files
        manifest = Manifest(
            title=title,
            name=packagename,
            description=description,
            version=version,
            version_packaged=__version__,
            version_min_required=min_checkmk_version,
            version_usable_until=None,
            author=author,
            download_url=download_url,
            files=manifest_files
        )
        json = manifest.to_json()
        tf = tarfile.TarInfo("info.json")
        tf.size = len(json)
        tarhandle.addfile(tf, io.BytesIO(json.encode("utf-8")))
        pp = manifest.to_pprint()
        tf = tarfile.TarInfo("info")
        tf.size = len(pp)
        tarhandle.addfile(tf, io.BytesIO(pp.encode("utf-8")))
    tar.seek(0)
    packagepath = os.path.join(_root, "build", packagename)
    with gzip.GzipFile(packagepath, "wb") as mkp:
        mkp.write(tar.read())
        mkp.flush()
    os.rename(packagepath, packagepath + ".mkp")


if __name__ == "__main__":
    package_purestorage_mpk()
