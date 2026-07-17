# Copyright (C) 2026 Fraser Cumming
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import shutil
import subprocess
import tempfile
import zlib

import processing
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsPalLayerSettings,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFile,
    QgsProject,
    QgsSymbol,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
)


class ImportCadDrawingAlgorithm(QgsProcessingAlgorithm):
    INPUT_FILE = "INPUT_FILE"
    INPUT_CRS = "INPUT_CRS"
    ODA_EXECUTABLE = "ODA_EXECUTABLE"

    def flags(self):
        # Layers are added and styled in the live project at the end of the run.
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FILE,
                self.tr("Input DWG or DXF drawing"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter=self.tr("CAD drawings (*.dwg *.dxf)"),
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.INPUT_CRS,
                self.tr("Drawing coordinate reference system"),
                defaultValue=None,
            )
        )
        oda_parameter = QgsProcessingParameterFile(
            self.ODA_EXECUTABLE,
            self.tr("ODA File Converter executable (required for DWG)"),
            behavior=QgsProcessingParameterFile.File,
            fileFilter=self.tr("ODA File Converter (ODAFileConverter.exe)"),
            optional=True,
        )
        oda_parameter.setHelp(
            self.tr(
                "Select ODAFileConverter.exe. If left empty on Windows, CAD Importer checks common installation folders."
            )
        )
        self.addParameter(oda_parameter)

    def processAlgorithm(self, parameters, context, feedback):
        input_path = self.parameterAsFile(parameters, self.INPUT_FILE, context)
        input_crs = self.parameterAsCrs(parameters, self.INPUT_CRS, context)
        oda_executable = self.parameterAsFile(parameters, self.ODA_EXECUTABLE, context)

        if not input_path or not os.path.isfile(input_path):
            raise QgsProcessingException(self.tr("The selected CAD drawing does not exist."))
        extension = os.path.splitext(input_path)[1].lower()
        if extension not in (".dwg", ".dxf"):
            raise QgsProcessingException(self.tr("Select a DWG or DXF drawing."))
        if not input_crs.isValid():
            raise QgsProcessingException(self.tr("Select a valid drawing CRS."))

        drawing_name = os.path.splitext(os.path.basename(input_path))[0]
        with tempfile.TemporaryDirectory(prefix="qgis_cad_importer_") as temp_dir:
            dxf_path = input_path
            if extension == ".dwg":
                dxf_path = self._convert_dwg(input_path, oda_executable, temp_dir, feedback)

            final_layers = self._prepare_layers(dxf_path, input_crs, context, feedback)
            if not final_layers:
                raise QgsProcessingException(self.tr("No supported point, line, or polygon features were found."))

            for layer in final_layers:
                self._name_and_style_layer(layer, drawing_name)
                QgsProject.instance().addMapLayer(layer)

        feedback.pushInfo(self.tr("Added {0} cleaned CAD layer(s) to the project.").format(len(final_layers)))
        return {}

    def _convert_dwg(self, input_path, selected_executable, temp_dir, feedback):
        executable = self._find_oda_executable(selected_executable)
        if not executable:
            raise QgsProcessingException(
                self.tr(
                    "ODA File Converter is required for DWG input. Install it separately, then select ODAFileConverter.exe in the algorithm dialog."
                )
            )

        input_dir = os.path.join(temp_dir, "input")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(input_dir)
        os.makedirs(output_dir)
        shutil.copy2(input_path, os.path.join(input_dir, os.path.basename(input_path)))

        environment = os.environ.copy()
        platforms_dir = os.path.join(os.path.dirname(executable), "platforms")
        if os.path.isdir(platforms_dir):
            environment["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms_dir

        feedback.pushInfo(self.tr("Converting DWG to a temporary DXF with ODA File Converter…"))
        try:
            completed = subprocess.run(
                [executable, input_dir, output_dir, "ACAD2018", "DXF", "0", "0"],
                cwd=os.path.dirname(executable),
                env=environment,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise QgsProcessingException(self.tr("ODA File Converter could not be started: {0}").format(error)) from error

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or self.tr("No diagnostic output was returned.")).strip()
            raise QgsProcessingException(
                self.tr("ODA File Converter failed with exit code {0}: {1}").format(completed.returncode, detail)
            )

        dxf_files = []
        for folder, _, files in os.walk(output_dir):
            dxf_files.extend(os.path.join(folder, name) for name in files if name.lower().endswith(".dxf"))
        if not dxf_files:
            raise QgsProcessingException(self.tr("ODA File Converter did not create a DXF file."))
        return dxf_files[0]

    @staticmethod
    def _find_oda_executable(selected_executable):
        candidates = [
            selected_executable,
            os.path.join(os.environ.get("ProgramFiles", ""), "ODA", "ODAFileConverter", "ODAFileConverter.exe"),
            r"C:\ODA File Converter\ODAFileConverter.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return os.path.normpath(candidate)
        return ""

    def _prepare_layers(self, dxf_path, input_crs, context, feedback):
        split_result = processing.run(
            "native:filterbygeometry",
            {
                "INPUT": dxf_path,
                "POINTS": QgsProcessing.TEMPORARY_OUTPUT,
                "LINES": QgsProcessing.TEMPORARY_OUTPUT,
                "POLYGONS": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        layers = [split_result[key] for key in ("POINTS", "LINES", "POLYGONS")]
        cleaned = []
        for layer in layers:
            if feedback.isCanceled():
                break
            if layer is None or layer.featureCount() == 0:
                continue
            layer = self._run("native:fixgeometries", {"INPUT": layer}, context, feedback)
            layer = self._run(
                "native:assignprojection", {"INPUT": layer, "CRS": input_crs}, context, feedback
            )
            empty_fields = [
                field.name()
                for field in layer.fields()
                if all(feature[field.name()] in (None, "", "NULL") for feature in layer.getFeatures())
            ]
            if empty_fields:
                layer = self._run(
                    "native:deletecolumn", {"INPUT": layer, "COLUMN": empty_fields}, context, feedback
                )
            before_count = layer.featureCount()
            layer = self._run("native:deleteduplicategeometries", {"INPUT": layer}, context, feedback)
            removed = before_count - layer.featureCount()
            if removed:
                feedback.pushWarning(self.tr("Removed {0} duplicate geometries.").format(removed))
            layer = self._add_measurement_fields(layer, context, feedback)
            cleaned.extend(self._split_by_cad_layer(layer, context, feedback))
        return cleaned

    @staticmethod
    def _run(algorithm_id, parameters, context, feedback):
        parameters["OUTPUT"] = QgsProcessing.TEMPORARY_OUTPUT
        return processing.run(
            algorithm_id,
            parameters,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )["OUTPUT"]

    def _add_measurement_fields(self, layer, context, feedback):
        if layer.fields().indexFromName("SubClasses") >= 0 and layer.fields().indexFromName("SubClass") < 0:
            layer = self._run(
                "native:fieldcalculator",
                {
                    "INPUT": layer,
                    "FIELD_NAME": "SubClass",
                    "FIELD_TYPE": 2,
                    "FIELD_LENGTH": 0,
                    "FIELD_PRECISION": 0,
                    "FORMULA": 'right("SubClasses", length("SubClasses") - 15)',
                },
                context,
                feedback,
            )
        geometry_type = layer.geometryType()
        if geometry_type == QgsWkbTypes.PolygonGeometry and layer.fields().indexFromName("Area") < 0:
            layer = self._measurement_field(layer, "Area", "$area", context, feedback)
        if geometry_type == QgsWkbTypes.LineGeometry and layer.fields().indexFromName("Length") < 0:
            layer = self._measurement_field(layer, "Length", "$length", context, feedback)
        return layer

    def _measurement_field(self, layer, name, expression, context, feedback):
        return self._run(
            "native:fieldcalculator",
            {
                "INPUT": layer,
                "FIELD_NAME": name,
                "FIELD_TYPE": 0,
                "FIELD_LENGTH": 0,
                "FIELD_PRECISION": 2,
                "FORMULA": expression,
            },
            context,
            feedback,
        )

    def _split_by_cad_layer(self, layer, context, feedback):
        if layer.fields().indexFromName("Layer") < 0:
            return [layer]
        values = sorted(
            {str(feature["Layer"]) for feature in layer.getFeatures() if feature["Layer"] not in (None, "", "NULL")}
        )
        results = []
        for value in values:
            results.append(
                self._run(
                    "native:extractbyattribute",
                    {"INPUT": layer, "FIELD": "Layer", "OPERATOR": 0, "VALUE": value},
                    context,
                    feedback,
                )
            )
        unassigned = self._run(
            "native:extractbyexpression",
            {"INPUT": layer, "EXPRESSION": '"Layer" IS NULL OR "Layer" IN (\'\', \'NULL\')'},
            context,
            feedback,
        )
        if unassigned.featureCount():
            results.append(unassigned)
        return results

    def _name_and_style_layer(self, layer, drawing_name):
        cad_layer_name = self.tr("No CAD Layer")
        if layer.fields().indexFromName("Layer") >= 0:
            values = sorted(
                {str(feature["Layer"]) for feature in layer.getFeatures() if feature["Layer"] not in (None, "", "NULL")}
            )
            if values:
                cad_layer_name = values[0]
        geometry_name = QgsWkbTypes.geometryDisplayString(layer.geometryType())
        layer_name = "{0} - {1} - {2}".format(drawing_name, cad_layer_name, geometry_name)
        layer.setName(re.sub(r'[<>:"/\\|?*]', "_", layer_name))

        if layer.fields().indexFromName("Text") >= 0:
            settings = QgsPalLayerSettings()
            settings.fieldName = "Text"
            settings.enabled = True
            layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
            layer.setLabelsEnabled(True)

        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        if symbol is not None:
            hue = zlib.crc32(layer.name().encode("utf-8")) % 360
            symbol.setColor(QColor.fromHsv(hue, 170, 210))
            layer.renderer().setSymbol(symbol)
        layer.triggerRepaint()

    def name(self):
        return "import_cad_drawing"

    def displayName(self):
        return self.tr("Import CAD drawing")

    def group(self):
        return self.tr("Import")

    def groupId(self):
        return "import"

    def shortHelpString(self):
        return self.tr(
            "Imports a DXF drawing or converts a DWG drawing through a separately installed ODA File Converter. "
            "Download ODA File Converter from https://www.opendesign.com/guestfiles/oda_file_converter. "
            "The tool assigns the selected CRS, repairs geometry, removes empty fields and duplicates, splits features "
            "by CAD layer and geometry type, and adds the resulting layers to the current QGIS project."
        )

    def createInstance(self):
        return ImportCadDrawingAlgorithm()

    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication

        return QCoreApplication.translate("ImportCadDrawingAlgorithm", message)
