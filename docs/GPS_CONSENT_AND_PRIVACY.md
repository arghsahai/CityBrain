# GPS-style location input and consent

## Implemented prototype

The Cesium operations page offers an explicit **Share this device location**
button and a **Stop location** button. Browser geolocation is requested only
after the user selects Share. The current prototype keeps the latest fix in
browser-tab memory only: it does not POST coordinates, save them to telemetry,
write them to disk, or send them to a traffic provider. Stop clears the browser
watch and removes the marker. Closing the tab also ends the watch.

The UI labels this input `CONSENTED DEVICE · LOCAL TAB ONLY`, shows accuracy and
timestamp, and matches it against local OSM road geometry. Fixes with accuracy
worse than 30 m, out-of-order times, reported speed over 55 m/s, impossible jumps,
ambiguous roads or no road within 15 m are rejected or shown as uncertain. A fix
ages to STALE after 15 seconds. It remains separate from SUMO ground-truth
vehicles and never enters planning or replanning.

Automated browser validation may emulate device coordinates. It does not access
a person's physical location. For a real device, use localhost or a secure
origin, grant the browser permission deliberately, and press Stop when finished.
The user can also revoke permission in browser settings.

## Not implemented

There is no GPS ingestion API, account identity, multi-device tracking,
persistent coordinate history, mobile app, background tracking, or CityBrain
runtime feed. Device fixes do not become emergency-vehicle state. Adding a
runtime input would require a separately reviewed authentication, consent,
retention and failure-isolation design. This prototype does not track arbitrary
cars or infer individual GPS traces from public traffic data.
