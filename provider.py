# Copyright (C) 2026 Fraser Cumming
# SPDX-License-Identifier: GPL-2.0-or-later

import os

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

from .processing.import_cad_drawing import ImportCadDrawingAlgorithm


class CadImporterProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(ImportCadDrawingAlgorithm())

    def id(self):
        return "cad_importer"

    def name(self):
        return "CAD Importer"

    def longName(self):
        return self.name()

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icons", "cad_importer.png"))
