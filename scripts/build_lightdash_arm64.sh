#!/usr/bin/env bash
# Construit l'image Lightdash pour ARM (arm64) à partir du code source officiel.
# L'image publiée sur Docker Hub n'existe qu'en amd64.
#
# Usage, sur le VPS : scripts/build_lightdash_arm64.sh 3.361.0
# Durée : environ 40 minutes sur 4 cœurs ARM.
set -euo pipefail

VERSION="${1:?version de Lightdash attendue, ex. 3.361.0}"
BUILD_DIR="$HOME/builds/lightdash"

rm -rf "$BUILD_DIR"
git clone --quiet --depth 1 --branch "$VERSION" \
    https://github.com/lightdash/lightdash.git "$BUILD_DIR"

cd "$BUILD_DIR"
nice -n 15 docker build -f dockerfile --target prod \
    -t "ecoshop/lightdash:${VERSION}-arm64" .

rm -rf "$BUILD_DIR"
echo "Image construite : ecoshop/lightdash:${VERSION}-arm64"
