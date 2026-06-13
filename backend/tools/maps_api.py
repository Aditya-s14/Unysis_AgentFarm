"""Distance matrix: Google Distance Matrix API with Haversine×1.3 fallback and Redis cache."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
from typing import Any

import httpx
import redis.asyncio as redis

from config import get_settings

# Max concurrent Google Maps API calls — stays well inside quota limits.
_GOOGLE_CONCURRENCY = 25

logger = logging.getLogger(__name__)

DIST_CACHE_PREFIX = "dist:"
DIST_CACHE_TTL_S = 3600
GOOGLE_DM_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
OSRM_ROUTE_PATH = "/route/v1/driving"
# OpenRouteService — hosted free routing engine. NOT OpenRouter (the LLM API).
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
EARTH_R_KM = 6371.0
ROAD_FACTOR = 1.3
# Max concurrent ORS calls — free tier is 40 req/min, so keep it low.
_ORS_CONCURRENCY = 10


def _pair_cache_key(a: tuple[float, float], b: tuple[float, float]) -> str:
    """Stable key for unordered pair (lat,lng)."""
    pa = f"{a[0]:.6f},{a[1]:.6f}"
    pb = f"{b[0]:.6f},{b[1]:.6f}"
    first, second = sorted([pa, pb])
    h = hashlib.sha256(f"{first}|{second}".encode("utf-8")).hexdigest()[:16]
    return f"{DIST_CACHE_PREFIX}{h}"


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in km × road factor (no external API)."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(h)))
    return float(EARTH_R_KM * c * ROAD_FACTOR)


async def _cached_distance_km(
    r: redis.Redis,
    a: tuple[float, float],
    b: tuple[float, float],
    computer: Any,
) -> float:
    key = _pair_cache_key(a, b)
    raw = await r.get(key)
    if raw is not None:
        return float(raw)
    d = float(computer(a, b))
    await r.set(key, f"{d:.6f}", ex=DIST_CACHE_TTL_S)
    return d


def _google_element_meters(
    el: dict[str, Any],
) -> float | None:
    st = el.get("status")
    if st != "OK":
        return None
    v = el.get("distance", {}).get("value")
    return float(v) / 1000.0 if v is not None else None


async def _ors_pair_km(
    client: httpx.AsyncClient,
    api_key: str,
    origin: tuple[float, float],
    dest: tuple[float, float],
) -> float | None:
    # ORS expects [lon, lat] like OSRM, not [lat, lng] like Google.
    payload = {
        "coordinates": [[origin[1], origin[0]], [dest[1], dest[0]]],
        "instructions": False,
        "geometry": False,
    }
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        resp = await client.post(
            ORS_DIRECTIONS_URL, json=payload, headers=headers, timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        routes = data.get("routes") or []
        if not routes:
            return None
        meters = routes[0].get("summary", {}).get("distance")
        return float(meters) / 1000.0 if meters is not None else None
    except Exception as exc:
        logger.warning("ORS distance failed: %r", exc)
        return None


async def _osrm_pair_km(
    client: httpx.AsyncClient,
    base_url: str,
    origin: tuple[float, float],
    dest: tuple[float, float],
) -> float | None:
    # OSRM expects lon,lat (not lat,lng like Google).
    coords = f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
    url = f"{base_url.rstrip('/')}{OSRM_ROUTE_PATH}/{coords}"
    try:
        resp = await client.get(url, params={"overview": "false"}, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            logger.warning("OSRM status %s", data.get("code"))
            return None
        routes = data.get("routes") or []
        if not routes:
            return None
        meters = routes[0].get("distance")
        return float(meters) / 1000.0 if meters is not None else None
    except Exception as exc:
        logger.warning("OSRM distance failed: %s", exc)
        return None


async def _google_pair_km(
    client: httpx.AsyncClient,
    api_key: str,
    origin: tuple[float, float],
    dest: tuple[float, float],
) -> float | None:
    params = {
        "origins": f"{origin[0]},{origin[1]}",
        "destinations": f"{dest[0]},{dest[1]}",
        "key": api_key,
        "units": "metric",
    }
    try:
        resp = await client.get(GOOGLE_DM_URL, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            logger.warning("Google DM status %s", data.get("status"))
            return None
        rows = data.get("rows") or []
        if not rows:
            return None
        elems = rows[0].get("elements") or []
        if not elems:
            return None
        km = _google_element_meters(elems[0])
        return km
    except Exception as exc:
        logger.warning("Google distance failed: %s", exc)
        return None


async def _cache_get(r: redis.Redis | None, key: str) -> float | None:
    if r is None:
        return None
    try:
        raw = await r.get(key)
        return float(raw) if raw is not None else None
    except Exception as exc:
        logger.debug("distance cache get failed: %s", exc)
        return None


async def _cache_set(r: redis.Redis | None, key: str, km: float) -> None:
    if r is None:
        return
    try:
        await r.set(key, f"{km:.6f}", ex=DIST_CACHE_TTL_S)
    except Exception as exc:
        logger.debug("distance cache set failed: %s", exc)


async def get_distance_matrix(
    origins: list[tuple[float, float]],
    destinations: list[tuple[float, float]],
) -> list[list[float]]:
    """
    Returns matrix ``[i][j]`` = km from ``origins[i]`` to ``destinations[j]``.

    Uses Google Distance Matrix when ``GOOGLE_MAPS_API_KEY`` is set; otherwise Haversine×1.3.
    Each pair is cached in Redis (TTL 1h).

    All pairs are resolved **concurrently** via asyncio.gather with a semaphore capping
    simultaneous Google API calls at _GOOGLE_CONCURRENCY.  This brings a 31-node matrix
    from ~96 s (sequential) down to ~3 s (cache-miss run) and <1 s (cache-hit).
    """
    settings = get_settings()
    api_key = (settings.GOOGLE_MAPS_API_KEY or "").strip()
    osrm_url = (settings.OSRM_URL or "").strip()
    ors_key = (settings.ORS_API_KEY or "").strip()
    n_o, n_d = len(origins), len(destinations)
    out: list[list[float]] = [[0.0] * n_d for _ in range(n_o)]

    r: redis.Redis | None = None
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.warning("distance matrix: Redis unavailable, skipping cache (%s)", exc)

    sem = asyncio.Semaphore(_GOOGLE_CONCURRENCY)
    ors_sem = asyncio.Semaphore(_ORS_CONCURRENCY)

    try:
        async with httpx.AsyncClient() as http_client:

            async def _resolve_pair(i: int, j: int) -> tuple[int, int, float]:
                a, b = origins[i], destinations[j]
                # Same location → zero cost
                if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
                    return i, j, 0.0

                cache_key = _pair_cache_key(a, b)

                cached = await _cache_get(r, cache_key)
                if cached is not None:
                    return i, j, cached

                # Primary: hosted OpenRouteService (free, no setup)
                if ors_key:
                    async with ors_sem:
                        o = await _ors_pair_km(http_client, ors_key, a, b)
                    if o is not None:
                        await _cache_set(r, cache_key, o)
                        return i, j, o

                # Secondary: self-hosted OSRM (if anyone prepped it)
                if osrm_url:
                    o = await _osrm_pair_km(http_client, osrm_url, a, b)
                    if o is not None:
                        await _cache_set(r, cache_key, o)
                        return i, j, o

                # Live Google Maps call (rate-limited by semaphore)
                if api_key:
                    async with sem:
                        g = await _google_pair_km(http_client, api_key, a, b)
                    if g is not None:
                        await _cache_set(r, cache_key, g)
                        return i, j, g

                # Haversine fallback (also cached when Redis is up)
                d = haversine_km(a, b)
                await _cache_set(r, cache_key, d)
                return i, j, d

            pairs = [
                _resolve_pair(i, j)
                for i in range(n_o)
                for j in range(n_d)
            ]
            results = await asyncio.gather(*pairs)

        for i, j, d in results:
            out[i][j] = d

    finally:
        if r is not None:
            await r.aclose()

    logger.debug(
        "get_distance_matrix: %dx%d matrix resolved (%d pairs)",
        n_o, n_d, n_o * n_d,
    )
    return out


# --- Road geometry (T7) -----------------------------------------------------
#
# Returns the road-snapped polyline through an ordered list of waypoints, as
# [[lat, lng], ...] ready for Leaflet. Provider order mirrors the distance
# matrix (ORS → OSRM); on total failure returns None and the frontend draws
# straight stop-to-stop lines, which is the pre-T7 behaviour.

GEOM_CACHE_PREFIX = "geom:"
GEOM_CACHE_TTL_S = 3600
ORS_GEOJSON_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
# Waypoints outside a provider's coverage get silently snapped to the nearest
# road in its graph (e.g. Delhi coords snap ~600 km away on a south-India OSRM
# extract) while still returning code=Ok. Reject geometry whose endpoints land
# further than this from the requested endpoints.
_SNAP_TOLERANCE_KM = 15.0


def _plausible_geometry(
    geometry: list[list[float]] | None,
    points: list[tuple[float, float]],
) -> bool:
    """True when geometry endpoints land near the requested endpoints."""
    if not geometry or len(geometry) < 2:
        return False
    start_ok = haversine_km((geometry[0][0], geometry[0][1]), points[0]) <= _SNAP_TOLERANCE_KM
    end_ok = haversine_km((geometry[-1][0], geometry[-1][1]), points[-1]) <= _SNAP_TOLERANCE_KM
    return start_ok and end_ok


def _geometry_cache_key(points: list[tuple[float, float]]) -> str:
    """Stable key for an ORDERED waypoint sequence (direction matters)."""
    joined = "|".join(f"{p[0]:.6f},{p[1]:.6f}" for p in points)
    h = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
    return f"{GEOM_CACHE_PREFIX}{h}"


def _flip_lnglat(coords: list[list[float]]) -> list[list[float]]:
    """GeoJSON is [lng, lat]; Leaflet wants [lat, lng]."""
    return [[float(c[1]), float(c[0])] for c in coords if len(c) >= 2]


async def _ors_route_geometry(
    client: httpx.AsyncClient,
    api_key: str,
    points: list[tuple[float, float]],
) -> list[list[float]] | None:
    payload = {
        "coordinates": [[p[1], p[0]] for p in points],
        "instructions": False,
        "geometry_simplify": True,
    }
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        resp = await client.post(
            ORS_GEOJSON_URL, json=payload, headers=headers, timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features") or []
        if not features:
            return None
        coords = features[0].get("geometry", {}).get("coordinates") or []
        return _flip_lnglat(coords) if len(coords) >= 2 else None
    except Exception as exc:
        logger.warning("ORS geometry failed: %r", exc)
        return None


async def _osrm_route_geometry(
    client: httpx.AsyncClient,
    base_url: str,
    points: list[tuple[float, float]],
) -> list[list[float]] | None:
    coords = ";".join(f"{p[1]},{p[0]}" for p in points)
    url = f"{base_url.rstrip('/')}{OSRM_ROUTE_PATH}/{coords}"
    params = {"overview": "simplified", "geometries": "geojson"}
    try:
        resp = await client.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            logger.warning("OSRM geometry status %s", data.get("code"))
            return None
        routes = data.get("routes") or []
        if not routes:
            return None
        coords_out = routes[0].get("geometry", {}).get("coordinates") or []
        return _flip_lnglat(coords_out) if len(coords_out) >= 2 else None
    except Exception as exc:
        logger.warning("OSRM geometry failed: %s", exc)
        return None


async def get_route_geometry(
    points: list[tuple[float, float]],
) -> list[list[float]] | None:
    """Road-snapped polyline [[lat, lng], ...] through ordered waypoints.

    Tries OpenRouteService, then self-hosted OSRM; result cached in Redis
    (TTL 1h). Returns None when no provider can answer — callers must treat
    that as "fall back to straight lines", never as an error.
    """
    if len(points) < 2:
        return None

    settings = get_settings()
    ors_key = (settings.ORS_API_KEY or "").strip()
    osrm_url = (settings.OSRM_URL or "").strip()

    r: redis.Redis | None = None
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.debug("route geometry: Redis unavailable, skipping cache (%s)", exc)

    cache_key = _geometry_cache_key(points)
    try:
        if r is not None:
            raw = await r.get(cache_key)
            if raw is not None:
                cached = json.loads(raw)
                return cached if cached else None

        geometry: list[list[float]] | None = None
        async with httpx.AsyncClient() as client:
            if ors_key:
                geometry = await _ors_route_geometry(client, ors_key, points)
                if geometry is not None and not _plausible_geometry(geometry, points):
                    logger.warning("ORS geometry implausible (snapped out of coverage?); discarding")
                    geometry = None
            if geometry is None and osrm_url:
                geometry = await _osrm_route_geometry(client, osrm_url, points)
                if geometry is not None and not _plausible_geometry(geometry, points):
                    logger.warning("OSRM geometry implausible (snapped out of coverage?); discarding")
                    geometry = None

        if r is not None and geometry is not None:
            try:
                await r.set(cache_key, json.dumps(geometry), ex=GEOM_CACHE_TTL_S)
            except Exception as exc:
                logger.debug("route geometry cache set failed: %s", exc)
        return geometry
    finally:
        if r is not None:
            await r.aclose()
