# CAD Importer

CAD Importer is a QGIS Processing plugin for importing and preparing DWG and DXF drawings.

## Features

- Imports DXF drawings directly.
- Converts DWG drawings to temporary DXF files through ODA File Converter.
- Assigns a user-selected coordinate reference system.
- Repairs geometries and removes duplicate features and empty fields.
- Adds area and length attributes where appropriate.
- Separates imported features by CAD layer and geometry type.
- Enables labels from the CAD `Text` field when available.
- Applies stable, contrasting colours to the imported layers.

## Requirements

- QGIS 3.28 or later.
- For DWG input on Windows: a separately installed copy of ODA File Converter.

ODA File Converter is not included with this plugin. Download it from the [official Open Design Alliance page](https://www.opendesign.com/guestfiles/oda_file_converter). Users are responsible for installing it separately and complying with its licence. DXF import does not require ODA File Converter.

## Installation

Install a released ZIP from **Plugins > Manage and Install Plugins > Install from ZIP**, or install the published version from the official QGIS Plugin Directory.

## Usage

1. Open **Vector > CAD Importer > CAD Importer**, or find **Import CAD drawing** in the Processing Toolbox.
2. Select a `.dwg` or `.dxf` drawing.
3. Use QGIS's standard CRS selector to choose the CRS used by the drawing. There is no default CRS. CAD formats may not contain reliable CRS metadata, so confirm this with the data supplier.
4. For a DWG drawing, select `ODAFileConverter.exe` if it is not found automatically.
5. Run the tool. Cleaned layers are added to the current project.

The tool does not reproject drawing coordinates. It assigns the CRS you select from the QGIS CRS database to the imported coordinates.

## Privacy and network access

CAD Importer processes drawings locally. It does not upload files or make network requests.

## Licence

CAD Importer is licensed under GPL-2.0-or-later. ODA File Converter is separate third-party software and is not distributed with this plugin.

Copyright (C) 2026 Fraser Cumming.

The icon artwork was supplied by Fraser Cumming and created using ChatGPT. CAD Importer is an independent community plugin and is not endorsed by or affiliated with QGIS.org or the Open Design Alliance.

## Support

Report bugs and request features through the [GitHub issue tracker](https://github.com/Fraser-Cumming-QGIS/CAD-Importer-for-QGIS/issues), or email `fraser.qgis.plugins.support@gmail.com`.

Source code is maintained at <https://github.com/Fraser-Cumming-QGIS/CAD-Importer-for-QGIS>.
