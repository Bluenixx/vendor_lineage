#!/bin/bash
# Bluenixx OTA json generator
# usage: createjson.sh <codename> <zip> [romtype]
DEVICE="$1"; ZIP="$2"; ROMTYPE="${3:-UNOFFICIAL}"
[ -f "$ZIP" ] || { echo "Zip not found: $ZIP"; exit 1; }
FILENAME=$(basename "$ZIP")
OUTDIR=$(dirname "$ZIP")
JSON="$OUTDIR/$DEVICE.json"
SHA256=$(sha256sum "$ZIP" | cut -d' ' -f1)
SIZE=$(stat -c %s "$ZIP")
DATETIME=$(grep -m1 '^ro.build.date.utc=' "$OUTDIR/system/build.prop" 2>/dev/null | cut -d= -f2)
[ -z "$DATETIME" ] && DATETIME=$(stat -c %Y "$ZIP")
VERSION=$(echo "$FILENAME" | cut -d- -f2)
case "$FILENAME" in *-OFFICIAL-*) ROMTYPE=OFFICIAL;; *-UNOFFICIAL-*) ROMTYPE=UNOFFICIAL;; esac
BASE_URL="${BLUENIXX_OTA_URL:-https://downloads.bluenixx.example}"
URL="$BASE_URL/$DEVICE/$FILENAME"
cat > "$JSON" <<JSONEOF
{
  "response": [
    {
      "datetime": $DATETIME,
      "filename": "$FILENAME",
      "id": "$SHA256",
      "romtype": "$ROMTYPE",
      "size": $SIZE,
      "url": "$URL",
      "version": "$VERSION"
    }
  ]
}
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
