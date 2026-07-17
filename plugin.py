# Copyright (C) 2026 Fraser Cumming
# SPDX-License-Identifier: GPL-2.0-or-later

import os

import processing
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication

from .provider import CadImporterProvider


class CadImporterPlugin:
    """Register the CAD Importer Processing provider and menu action."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None
        self.menu_name = self.tr("&CAD Importer")

    def tr(self, message):
        return QCoreApplication.translate("CadImporterPlugin", message)

    def initProcessing(self):
        if self.provider is None:
            self.provider = CadImporterProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        # qgis_process loads Processing providers without a desktop interface.
        if self.iface is None:
            return

        icon_path = os.path.join(os.path.dirname(__file__), "icons", "cad_importer.png")
        self.action = QAction(QIcon(icon_path), self.tr("CAD Importer"), self.iface.mainWindow())
        self.action.setObjectName("CadImporterAction")
        help_text = self.tr("Import and prepare a DWG or DXF drawing in QGIS.")
        self.action.setWhatsThis(help_text)
        self.action.setStatusTip(help_text)
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu(self.menu_name, self.action)

    def unload(self):
        if self.action is not None and self.iface is not None:
            self.iface.removePluginVectorMenu(self.menu_name, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def run(self):
        if self.iface is not None:
            processing.execAlgorithmDialog("cad_importer:import_cad_drawing", {})
