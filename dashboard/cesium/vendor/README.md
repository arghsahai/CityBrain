# CesiumJS 1.121.0

The `Cesium/` directory is the unmodified production build from the npm archive
recorded in `manifest.json`. Apache-2.0 license and upstream third-party notices
are retained beside it. The manifest records a SHA-256 for each distributed file.
This pinned local build makes the baseline globe and evidence replay independent
of CDNs, Cesium ion, and API credentials. It uses WGS84 ellipsoid terrain.

OSM raster tiles are an optional user-selected layer fetched from
`https://tile.openstreetmap.org/`. No bulk download or offline tile cache is used.
Road/building geometry is local OSM-derived data under ODbL-1.0. Required OSM
attribution is visible in the map UI and the Cesium credit area.
