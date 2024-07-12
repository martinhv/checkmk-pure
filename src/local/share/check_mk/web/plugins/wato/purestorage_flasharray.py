#!/usr/bin/env python3

# This file registers the WATO (web interface) plugin for the configuration form. Since this file is loaded using
# eval() and cannot be interactively debugged, it serves as an indirection point.

from cmk.gui.watolib.rulespecs import rulespec_registry
from purestorage_checkmk.flasharray import wato

wato.init(rulespec_registry)
