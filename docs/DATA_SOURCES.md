# Data Sources

## MaxMind

GeoLocate Tracker uses a provider adapter around MaxMind GeoIP/GeoLite web
services.

MaxMind documents City, Country, and Insights web-service endpoints and
requires HTTPS authentication using an account ID and license key.

The exact fields available depend on the MaxMind service/product licensed by
the deployment.

Provider documentation:

https://dev.maxmind.com/geoip/docs/web-services/

API request documentation:

https://dev.maxmind.com/geoip/docs/web-services/requests/

MaxMind explicitly states that IP geolocation is inherently imprecise and
that GeoIP locations should not be used to identify a particular address or
household.

## Python ipaddress

The backend uses Python's standard `ipaddress` module.

It provides IPv4/IPv6 parsing and properties such as:

- `is_private`
- `is_global`
- `is_loopback`
- `is_multicast`
- `is_unspecified`
- `is_reserved`
- `is_link_local`

Documentation:

https://docs.python.org/3/library/ipaddress.html

## Leaflet

Leaflet provides:

- interactive maps
- tile layers
- markers
- circles
- popups
- controls

Documentation:

https://leafletjs.com/reference/

Quick start:

https://leafletjs.com/examples/quick-start/

## OpenStreetMap

The development/default tile configuration uses:

```text
https://tile.openstreetmap.org/{z}/{x}/{y}.png