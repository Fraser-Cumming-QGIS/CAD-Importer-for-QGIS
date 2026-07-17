# Copyright (C) 2026 Fraser Cumming
# SPDX-License-Identifier: GPL-2.0-or-later
"""QGIS entry point for CAD Importer."""


def classFactory(iface):
    from .plugin import CadImporterPlugin

    return CadImporterPlugin(iface)
