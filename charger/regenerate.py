#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# Renders every charger asset in Material 3 Expressive style:
#   <density>/battery_scale.png  22 frames, row-interleaved, "Frames" tEXt chunk
#   <density>/battery_fail.png   unknown/missing battery
#   <density>/percent_font.png   96x2 glyph grid (only 0-9 and % are drawn)
#
# Frame i (1..19) is the ring filled to i * 5 %, frame 0 is empty, frame 20 is
# a (almost) full wavy ring, frame 21 is the calm "fully charged" ring. The
# charger alternates between two neighbouring frames (see animation.txt), so
# every frame also shifts the wave phase and morphs/rotates the cookie shape
# to keep the screen alive.
#
# Requirements: python3, numpy, scipy, opencv-python, pillow.
# The digits use Poppins Medium (SIL OFL 1.1). Point POPPINS_TTF at the file
# if it is not in one of the default locations.
#

import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))

DENSITIES = {"mdpi": 160, "hdpi": 240, "xhdpi": 320, "xxhdpi": 480, "xxxhdpi": 640}
FRAMES = 22

# Everything is drawn once on a master canvas that is an integer multiple of
# every density, then area-averaged down (clean anti-aliasing).
MASTER = 2560
PX = MASTER / 300.0  # master pixels per design unit (design canvas is 300x300)

# --- Material 3 dark scheme (baseline tonal palette) ------------------------
def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)

BLACK = hexc("000000")
SURFACE_DISC = hexc("16131B")
TRACK = hexc("36343B")             # surfaceContainerHighest
PRIMARY = hexc("D0BCFF")
PRIMARY_CONTAINER = hexc("4F378B")
ON_PRIMARY_CONTAINER = hexc("EADDFF")
ON_PRIMARY = hexc("381E72")
ERROR_CONTAINER = hexc("8C1D18")
ON_ERROR_CONTAINER = hexc("F9DEDC")
ON_SURFACE = (230, 224, 233)       # percent text colour, goes in animation.txt

# --- Geometry, in design units ----------------------------------------------
RING_R = 126.0       # centre line radius
RING_W = 10.0        # half thickness (stroke = 20)
WAVE_A = 5.0         # wave amplitude
WAVE_K = 12          # waves around the full circle
GAP = 8.0            # gap between active indicator and track
COOKIE_C = (150.0, 202.0)
COOKIE_R = 25.0

# Text layout inside the font cell, relative to the screen centre (units).
TEXT_CENTER_DY = -28.0
DIGIT_H = 46.0
CELL_W = 41.0
CELL_H = 120.0       # char_height = font png height / 2


# =============================================================================
# master canvas helpers
# =============================================================================
_yy, _xx = np.mgrid[0:MASTER, 0:MASTER].astype(np.float32)
_X = (_xx + 0.5) / PX - 150.0
_Y = (_yy + 0.5) / PX - 150.0
del _yy, _xx
_R = np.hypot(_X, _Y)


def new_canvas():
    return np.zeros((MASTER, MASTER, 3), np.float32)


def paint(canvas, alpha, color):
    a = alpha[..., None]
    canvas *= 1.0 - a
    canvas += a * np.asarray(color, np.float32)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def tube(points_u, half_w_u, closed=False):
    """Soft alpha of a round-capped stroke along a poly-line (design units)."""
    pts = np.round(points_u * PX).astype(np.int32)
    pts = np.clip(pts, 0, MASTER - 1)
    img = np.zeros((MASTER, MASTER), np.uint8)
    img[pts[:, 1], pts[:, 0]] = 255
    cv2.polylines(img, [pts.reshape(-1, 1, 2)], closed, 255, 1)
    dist = ndi.distance_transform_edt(img == 0).astype(np.float32)
    return np.clip(half_w_u * PX - dist + 0.5, 0.0, 1.0)


def polar_pts(theta, radius):
    return np.stack([150 + radius * np.sin(theta), 150 - radius * np.cos(theta)], 1)


def disc(radius):
    return np.clip((radius - _R) * PX + 0.5, 0.0, 1.0)


def lobed(cx, cy, radius, lobes, depth, rot, scale=1.0):
    """Soft alpha of a 'cookie' style shape r = R (1 + d cos(n (a - rot)))."""
    dx, dy = _X - (cx - 150.0), _Y - (cy - 150.0)
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    base = radius * scale
    f = base * (1 + depth * np.cos(lobes * (ang - rot)))
    fp = -base * depth * lobes * np.sin(lobes * (ang - rot))
    sd = (r - f) / np.sqrt(1 + (fp / np.maximum(r, 1e-3)) ** 2)
    return np.clip(0.5 - sd * PX, 0.0, 1.0)


# =============================================================================
# icons
# =============================================================================
BOLT = np.array([(13.2, 2.0), (5.0, 13.4), (10.6, 13.4), (9.4, 22.0),
                 (19.0, 9.8), (13.4, 9.8)], np.float32)
CHECK = np.array([(6.8, 12.6), (10.4, 16.2), (17.4, 8.4)], np.float32)


def bolt_alpha(cx, cy, height, round_u=1.4):
    pts = BOLT.copy()
    pts -= pts.mean(0)
    pts *= (height - 2 * round_u) / (BOLT[:, 1].max() - BOLT[:, 1].min())
    pts += (cx, cy)
    img = np.zeros((MASTER, MASTER), np.uint8)
    p = np.round(pts * PX * 8).astype(np.int32)
    cv2.fillPoly(img, [p.reshape(-1, 1, 2)], 255, cv2.LINE_AA, 3)
    cv2.polylines(img, [p.reshape(-1, 1, 2)], True, 255,
                  int(round(2 * round_u * PX)), cv2.LINE_AA, 3)
    return img.astype(np.float32) / 255.0


def check_alpha(cx, cy, size, stroke_u=3.6):
    pts = CHECK.copy()
    pts -= (pts.min(0) + pts.max(0)) / 2
    pts *= size / (CHECK[:, 0].max() - CHECK[:, 0].min())
    pts += (cx, cy)
    return tube_poly(pts, stroke_u / 2)


def tube_poly(pts_u, half_w_u):
    """Same as tube() but densifies a coarse poly-line first."""
    out = []
    for a, b in zip(pts_u[:-1], pts_u[1:]):
        n = max(2, int(np.linalg.norm(b - a) * PX))
        t = np.linspace(0, 1, n)[:, None]
        out.append(a + (b - a) * t)
    return tube(np.concatenate(out), half_w_u)


# =============================================================================
# frames
# =============================================================================
def ring(canvas, p, phase, amp, flat_done=False):
    """Track + wavy active indicator for progress p (0..1)."""
    R, w = RING_R, RING_W
    cap, gap = w / R, GAP / R
    th1 = cap
    th3 = 2 * math.pi - gap - cap
    delta = (2 * w + GAP) / R
    span = th3 - delta - th1

    if p >= 0.999:
        n = int(2 * math.pi * R * PX * 1.2)
        th = np.linspace(0, 2 * math.pi, n, endpoint=False)
        pts = polar_pts(th, R + amp * np.sin(WAVE_K * th - phase))
        paint(canvas, tube(pts, w, closed=True), PRIMARY)
        return

    th2 = th1 + p * span
    # track (flat arc)
    t0 = th2 + delta
    if t0 < th3:
        th = np.linspace(t0, th3, max(2, int((th3 - t0) * R * PX * 1.2)))
        paint(canvas, tube(polar_pts(th, np.full_like(th, R)), w), TRACK)

    # active (wavy arc)
    n = max(2, int((th2 - th1) * R * PX * 1.2))
    th = np.linspace(th1, th2, n)
    e = min(14.0 / R, (th2 - th1) / 2 + 1e-6)
    env = smoothstep((th - th1) / e) * smoothstep((th2 - th) / e) if th2 > th1 else 0 * th
    pts = polar_pts(th, R + amp * env * np.sin(WAVE_K * th - phase))
    paint(canvas, tube(pts, w), PRIMARY)


def draw_scale_frame(i):
    full = i == 20
    done = i == 21
    p = 0.0 if i == 0 else 1.0 if (full or done) else i / 20.0
    phase = (i % 4) * math.pi / 2
    amp = 0.0 if done else WAVE_A

    c = new_canvas()
    paint(c, disc(RING_R - RING_W - WAVE_A - 5), SURFACE_DISC)
    ring(c, p, phase, amp)

    odd = i % 2
    cx, cy = COOKIE_C
    rot = odd * math.pi / 9          # half a lobe: peaks <-> valleys
    scale = 1.0 + 0.07 * odd
    if done:
        paint(c, lobed(cx, cy, COOKIE_R, 9, 0.065, 0.0, 1.05), PRIMARY)
        paint(c, check_alpha(cx, cy, 20), ON_PRIMARY)
    else:
        paint(c, lobed(cx, cy, COOKIE_R, 9, 0.065, rot, scale), PRIMARY_CONTAINER)
        paint(c, bolt_alpha(cx, cy, 25.0 * (1.0 + 0.04 * odd)), ON_PRIMARY_CONTAINER)
    return c


def question_alpha(cx, cy, height):
    font = ImageFont.truetype(find_font(), 400)
    l, t, r, b = font.getbbox("?")
    k = height * PX / (b - t)
    font = ImageFont.truetype(find_font(), int(400 * k))
    l, t, r, b = font.getbbox("?")
    im = Image.new("L", (MASTER, MASTER), 0)
    ImageDraw.Draw(im).text((cx * PX - (l + r) / 2, cy * PX - (t + b) / 2), "?", 255, font=font)
    return np.asarray(im, np.float32) / 255.0


def draw_fail_frame():
    c = new_canvas()
    paint(c, lobed(150, 150, 128, 12, 0.075, 0.0), ERROR_CONTAINER)
    paint(c, disc(92), hexc("6B1612"))
    paint(c, question_alpha(150, 150, 96), ON_ERROR_CONTAINER)
    return c


# =============================================================================
# font
# =============================================================================
def find_font():
    for p in (os.environ.get("POPPINS_TTF", ""),
              "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf",
              "/usr/share/fonts/truetype/poppins/Poppins-Medium.ttf",
              os.path.expanduser("~/.fonts/Poppins-Medium.ttf")):
        if p and os.path.exists(p):
            return p
    sys.exit("Poppins-Medium.ttf not found, set POPPINS_TTF")


def make_font(width_px):
    s = width_px / 300.0
    cw, ch = round(CELL_W * s), round(CELL_H * s)
    digit_h = DIGIT_H * s
    path = find_font()

    probe = ImageFont.truetype(path, 200)
    l, t, r, b = probe.getbbox("0")
    size = int(round(200 * digit_h / (b - t)))
    f_digit = ImageFont.truetype(path, size)
    f_pct = ImageFont.truetype(path, int(round(size * 0.74)))

    img = Image.new("L", (96 * cw, 2 * ch), 0)
    d = ImageDraw.Draw(img)
    # baseline so that the digits are centred TEXT_CENTER_DY above the middle
    l, t, r, b = f_digit.getbbox("0")
    ink_h = b - t
    top = ch / 2 + TEXT_CENTER_DY * s - ink_h / 2
    base_y = top - t  # text() origin such that '0' ink top lands on `top`
    for ch_ in "0123456789%":
        f = f_pct if ch_ == "%" else f_digit
        l, t2, r, b2 = f.getbbox(ch_)
        x = (ord(ch_) - 32) * cw + (cw - (r - l)) / 2 - l
        if ch_ == "%":
            y = top + ink_h - b2          # sit on the same baseline as digits
        else:
            y = base_y
        d.text((x, y), ch_, 255, font=f)
    return img


# =============================================================================
# output
# =============================================================================
def down(master, size):
    out = cv2.resize(master, (size, size), interpolation=cv2.INTER_AREA)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def write_interleaved(frames, path):
    n = len(frames)
    h = frames[0].shape[0]
    stacked = np.zeros((h * n, frames[0].shape[1], 3), np.uint8)
    for f, fr in enumerate(frames):
        stacked[f::n] = fr           # row y of frame f -> row y*n + f
    info = PngImagePlugin.PngInfo()
    info.add_text("Frames", str(n))
    Image.fromarray(stacked, "RGB").save(path, pnginfo=info, optimize=True)


def main():
    scale = {name: [] for name in DENSITIES}
    for i in range(FRAMES):
        m = draw_scale_frame(i)
        for name, wpx in DENSITIES.items():
            scale[name].append(down(m, wpx))
        print("frame", i, flush=True)
    fail = draw_fail_frame()
    for name, wpx in DENSITIES.items():
        d = os.path.join(HERE, name)
        os.makedirs(d, exist_ok=True)
        write_interleaved(scale[name], os.path.join(d, "battery_scale.png"))
        Image.fromarray(down(fail, wpx), "RGB").save(os.path.join(d, "battery_fail.png"), optimize=True)
        make_font(wpx).save(os.path.join(d, "percent_font.png"), optimize=True)
        print("done", name)


if __name__ == "__main__":
    main()
