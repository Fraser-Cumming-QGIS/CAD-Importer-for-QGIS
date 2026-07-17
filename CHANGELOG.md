# Changelog

## 0.1.0

- Renamed the plugin to CAD Importer.
- Added an explicit ODA File Converter executable parameter.
- Removed the region-specific default CRS and used QGIS's standard CRS selector with no default.
- Removed runtime installation of third-party Python packages.
- Converted DWG drawings in temporary working directories instead of beside source data.
- Added clearer validation and conversion errors.
- Added support for headless provider loading through `qgis_process`.
- Added the official ODA File Converter download link to plugin and algorithm help.
- Replaced the plugin icon with artwork supplied by the maintainer.
- Preserved geometry repair, cleanup, CAD-layer splitting, labelling and styling.
- Added publication metadata and user documentation.
