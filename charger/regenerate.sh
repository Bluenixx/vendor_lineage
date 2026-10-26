#!/bin/bash
#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# Re-renders every PNG in this folder (Material 3 Expressive style).
# Needs: python3, numpy, scipy, opencv-python, pillow and Poppins-Medium.ttf
# (set POPPINS_TTF=/path/to/Poppins-Medium.ttf if it is not auto-detected).

set -e
cd "$(dirname "$0")"

for mod in numpy scipy cv2 PIL; do
    python3 -c "import $mod" 2>/dev/null || {
        echo "Missing python module: $mod (pip install numpy scipy opencv-python pillow)"
        exit 1
    }
done

exec python3 regenerate.py
