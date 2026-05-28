#!/usr/bin/env bash
# One-time OSRM map preparation for AgentFarm Optimizer (Mac / Linux).
#
# Downloads South + West India OpenStreetMap data (covers Karnataka, Tamil Nadu,
# Kerala, Andhra Pradesh, Telangana, Pondicherry, Maharashtra, Gujarat, Goa,
# Daman & Diu, Dadra & Nagar Haveli), merges them into a single PBF with
# osmium-tool, and runs OSRM's three pre-processing steps. Idempotent.
#
# After this completes:   docker compose up -d
# To force re-prep:       docker volume rm osrm_data ; then re-run this script.

set -euo pipefail

SOUTH_URL="https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"
SOUTH_PBF="southern-zone-latest.osm.pbf"
WEST_URL="https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf"
WEST_PBF="western-zone-latest.osm.pbf"
MERGED_PBF="india-south-west.osm.pbf"
OSRM_NAME="india-south-west.osrm"
VOLUME="osrm_data"
OSRM_IMG="osrm/osrm-backend:latest"
OSMIUM_IMG="debian:bookworm-slim"

GREEN="\033[0;32m"
CYAN="\033[0;36m"
RED="\033[0;31m"
NC="\033[0m"

log()  { printf "${CYAN}==> %s${NC}\n" "$*"; }
ok()   { printf "${GREEN}==> %s${NC}\n" "$*"; }
fail() { printf "${RED}%s${NC}\n" "$*" >&2; exit 1; }

has_file() {
    docker run --rm -v "${VOLUME}:/data" alpine sh -c "test -f /data/$1 && echo YES || echo NO" \
        | grep -q YES
}

get_pbf() {
    local url="$1" name="$2"
    if has_file "$name"; then
        ok "$name already downloaded. Skipping."
        return
    fi
    log "Downloading $name..."
    docker run --rm -v "${VOLUME}:/data" alpine sh -c \
        "cd /data && wget -O $name $url"
}

log "Checking Docker..."
docker info --format "{{.ServerVersion}}" >/dev/null 2>&1 \
    || fail "Docker is not running. Start it first."

log "Ensuring volume $VOLUME exists..."
docker volume create "$VOLUME" >/dev/null

if has_file "$OSRM_NAME.fileIndex"; then
    ok "OSRM data already prepared. Skipping."
    echo "    To re-prep from scratch: docker volume rm $VOLUME"
    exit 0
fi

get_pbf "$SOUTH_URL" "$SOUTH_PBF"
get_pbf "$WEST_URL"  "$WEST_PBF"

if ! has_file "$MERGED_PBF"; then
    log "Merging South + West zones into $MERGED_PBF..."
    docker run --rm -v "${VOLUME}:/data" "$OSMIUM_IMG" bash -c \
        "apt-get update -qq && apt-get install -y -qq --no-install-recommends osmium-tool && osmium merge /data/$SOUTH_PBF /data/$WEST_PBF -o /data/$MERGED_PBF"
else
    ok "Merged PBF already present. Skipping."
fi

if ! has_file "$OSRM_NAME"; then
    log "Running osrm-extract (car profile)..."
    docker run --rm -v "${VOLUME}:/data" "$OSRM_IMG" \
        osrm-extract -p /opt/car.lua "/data/$MERGED_PBF"
else
    ok "Extract already done. Skipping."
fi

if ! has_file "$OSRM_NAME.partition"; then
    log "Running osrm-partition..."
    docker run --rm -v "${VOLUME}:/data" "$OSRM_IMG" \
        osrm-partition "/data/$OSRM_NAME"
else
    ok "Partition already done. Skipping."
fi

log "Running osrm-customize..."
docker run --rm -v "${VOLUME}:/data" "$OSRM_IMG" \
    osrm-customize "/data/$OSRM_NAME"

echo
ok "OSRM data prepared (South + West India)."
echo "    Start the stack: docker compose up -d"
