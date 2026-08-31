#!/usr/bin/env bash
#
# Build the not1mm flatpak from the current source tree.
#
# Must be run on a Linux host with flatpak and flatpak-builder installed
# (flatpak cannot be built on macOS). x86_64 is the primary target since the
# pinned wheels in python3-modules.yaml are x86_64-only.
#
#   ./build_flatpak.sh
#
# Produces:
#   build/          - the flatpak-builder build directory
#   flatpak-repo/   - the OSTree repository
#   not1mm.flatpak  - installable single-file bundle
#
# Install locally with:
#   flatpak install --user not1mm.flatpak

set -euo pipefail
cd "$(dirname "$0")"

flatpak-builder --force-clean --repo=flatpak-repo build io.github.mbridak.not1mm.yaml "$@"
flatpak build-bundle flatpak-repo not1mm.flatpak io.github.mbridak.not1mm

echo "Built not1mm.flatpak"
