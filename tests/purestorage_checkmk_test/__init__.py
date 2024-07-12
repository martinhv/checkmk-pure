import os
import sys


def add_checkmk_import_paths():
    """
    This function adds the checkmk plugin library as a path, so we can import it. This is needed because
    this is not a normal Python package.
    """
    checkmk_lib_path = os.path.abspath(
        os.path.join(__file__, "../../../src/local/lib/python3")
    )

    if checkmk_lib_path not in sys.path:
        sys.path.insert(
            0,
            checkmk_lib_path
        )

    checkmk_path = os.path.abspath(
        os.path.join(__file__, "../../../checkmk")
    )

    if checkmk_path not in sys.path:
        sys.path.insert(
            0,
            checkmk_path
        )
