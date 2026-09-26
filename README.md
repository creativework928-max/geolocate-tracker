# GeoLocate Tracker

Professional real-time IP intelligence and approximate geolocation dashboard.

GeoLocate Tracker accepts IPv4 and IPv6 addresses, resolves them through a
configured GeoIP provider, normalizes the result through a provider-neutral
backend model, and visualizes the approximate geographic position with
Leaflet.

## Important limitation

IP geolocation provides an approximate geographic location.

It does not identify:

- an exact street address
- a household
- an exact physical position
- continuous physical movement

The application therefore uses terms such as "approximate location",
"estimated position", and "IP-derived location".

## Features

- IPv4 lookup
- IPv6 lookup
- Automatic requesting-client IP detection
- MaxMind provider adapter
- Provider abstraction
- Pydantic response models
- FastAPI REST API
- Interactive Leaflet map
- Accuracy-radius visualization when supplied
- Input validation
- Private/reserved IP rejection
- Configurable rate limiting
- Configurable in-memory TTL cache
- Security headers
- Configurable CORS
- Explicit trusted-proxy handling
- Privacy-conscious logging
- Demo mode
- Docker deployment
- Automated tests
- OpenAPI / Swagger documentation
- ReDoc documentation

## Architecture

Browser

↓

FastAPI

↓

IP validation

↓

Cache

↓

GeoLocationService

↓

GeoLocationProvider

↓

MaxMind

↓

Normalized GeoLocation

↓

JSON API

↓

Leaflet dashboard

## Requirements

- Python 3.12+
- Docker and Docker Compose for container deployment
- MaxMind GeoIP/GeoLite credentials for live provider lookups

## Local installation

Clone the repository and enter it:

```bash
cd geolocate-tracker