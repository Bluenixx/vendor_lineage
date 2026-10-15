#!/bin/bash
# Bluenixx OTA json generator (Lineage Updater v2 format)
# usage: createjson.sh <codename> <zip> [romtype]
DEVICE="$1"; ZIP="$2"
[ -f "$ZIP" ] || { echo "Zip not found: $ZIP"; exit 1; }
FILENAME=$(basename "$ZIP")
OUTDIR=$(dirname "$ZIP")
JSON="$OUTDIR/$DEVICE.json"
SHA256=$(sha256sum "$ZIP" | cut -d' ' -f1)
SIZE=$(stat -c %s "$ZIP")
META=$(unzip -p "$ZIP" META-INF/com/android/metadata 2>/dev/null)
meta() { echo "$META" | grep -m1 "^$1=" | cut -d= -f2-; }
PATCH=$(meta post-security-patch-level)
SDK=$(meta post-sdk-level)
PROPS=$(meta ota-property-files)
if [ -z "$PATCH" ] || [ -z "$SDK" ] || [ -z "$PROPS" ]; then
  echo "OTA json skipped: metadata missing in $FILENAME"; exit 0
fi
DATETIME=$(grep -m1 '^ro.build.date.utc=' "$OUTDIR/system/build.prop" 2>/dev/null | cut -d= -f2)
[ -z "$DATETIME" ] && DATETIME=$(meta post-timestamp)
[ -z "$DATETIME" ] && DATETIME=$(stat -c %Y "$ZIP")
VERSION=$(echo "$FILENAME" | cut -d- -f2)
TYPE="${BLUENIXX_OTA_TYPE:-nightly}"
BASE_URL="${BLUENIXX_OTA_URL:-https://downloads.bluenixx.example}"
URL="$BASE_URL/$DEVICE/$FILENAME"
cat > "$JSON" <<JSONEOF
[
  {
    "datetime": $DATETIME,
    "files": [
      {
        "filename": "$FILENAME",
        "os_patch_level": "$PATCH",
        "os_sdk_level": $SDK,
        "ota_property_files": "$PROPS",
        "sha256": "$SHA256",
        "size": $SIZE,
        "url": "$URL"
      }
    ],
    "type": "$TYPE",
    "version": "$VERSION"
  }
]
JSONEOF
CYAN='\033[1;36m'; GRN='\033[1;32m'; NC='\033[0m'
echo -e "\n${GRN}OTA json: $JSON${NC}\n"
cat "$JSON"
echo -e "${CYAN}"
cat <<'BANNER'
██████╗ ██╗     ██╗   ██╗███████╗███╗   ██╗██╗██╗  ██╗██╗  ██╗
██╔══██╗██║     ██║   ██║██╔════╝████╗  ██║██║╚██╗██╔╝╚██╗██╔╝
██████╔╝██║     ██║   ██║█████╗  ██╔██╗ ██║██║ ╚███╔╝  ╚███╔╝
██╔══██╗██║     ██║   ██║██╔══╝  ██║╚██╗██║██║ ██╔██╗  ██╔██╗
██████╔╝███████╗╚██████╔╝███████╗██║ ╚████║██║██╔╝ ██╗██╔╝ ██╗
╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
BANNER
echo -e "${NC}${GRN}      Thank you for building Bluenixx!${NC}\n"
