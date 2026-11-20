# import pygame
# import cv2
# import numpy as np
# import random
# import math

# # ---------------- SETTINGS ----------------
# pygame.init()
# W, H = 700, 800
# screen = pygame.display.set_mode((W, H))
# pygame.display.set_caption("Code With Love")
# clock = pygame.time.Clock()

# BG = (8, 5, 15)
# FPS = 60
# random.seed(7)
# np.random.seed(7)

# IMAGE_PATH = "anime1.jpg"
# QUOTE = "They Called It A Punishment.\nShe Called It Armor."
# FOCUS_REL = (0.50, 0.24)   # where the tracing starts, relative to the figure (x, y) - the face

# # --- timeline (seconds) ---
# TRACE_START = 0.2     # first line segments start here
# TRACE_SPREAD = 7.5    # segments start one after another over this time, from the face outwards
# SEG_LEN = 140         # length of one line segment (pixels)
# SEG_SPEED = 60        # how fast the bright "pen" runs along a segment (pixels / second)
# SEG_MIN_DUR = 1.5
# SEG_MAX_DUR = 3.0
# FILL_START = 7.0      # color starts to fill the figure
# FILL_END = 13.0       # ...and has covered it all
# SHIMMER_START = 13.4  # a light sweeps over the finished figure
# SHIMMER_DUR = 2.4
# TEXT_START = 14.6     # the quote appears word by word
# WORD_GAP = 0.35
# WORD_DUR = 1.6
# TWINKLES = 45         # little sparkles that flash on the lines
# FADE_START = 22.0     # everything fades out...
# DURATION = 24.0       # ...and the animation starts again

# # colors from top to bottom of the figure (gold -> teal -> blue -> purple)
# STOPS = np.array([(255, 215, 140), (120, 230, 200), (90, 175, 240), (170, 130, 240)],
#                  dtype=np.float32)

# TRACE_COL = np.array((110, 150, 190), dtype=np.float32)   # color of a line before it is filled
# INK_DARK = np.array((6, 10, 24), dtype=np.float32)        # color of the lines on the finished figure
# BAND_COL = np.array((175, 170, 205), dtype=np.float32)    # soft light band at the front of the fill
# SOFT = 36                                                  # softness of the fill front (pixels)


# # ---------------- EASING + COLOR ----------------
# def ease_in_out(x):
#     return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


# def ease_sine(x):
#     return -(math.cos(math.pi * x) - 1) / 2


# def ease_out(x):
#     return 1 - (1 - x) ** 3


# def palette(g):
#     """g in 0..1 (numpy array or number) -> RGB color from STOPS."""
#     g = np.clip(g, 0, 1) * (len(STOPS) - 1)
#     i = np.minimum(np.asarray(g).astype(int), len(STOPS) - 2)
#     f = (g - i)[..., None] if np.ndim(g) else (g - i)
#     return STOPS[i] * (1 - f) + STOPS[i + 1] * f


# # ---------------- IMAGE -> INK LINES + FIGURE SHAPE ----------------
# def find_figure(gray):
#     """Return (ink, silhouette) masks of a gray image (ink = dark lines)."""
#     ink = (gray < 128).astype(np.uint8)
#     body = (gray < 235).astype(np.uint8) | ink              # figure = anything that is not white
#     body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
#     n, lab, st, _ = cv2.connectedComponentsWithStats(body)
#     if n > 1:
#         body = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
#     pad = np.pad(1 - body, 1, constant_values=1).astype(np.uint8)
#     cv2.floodFill(pad, None, (0, 0), 2)                     # fill the outside, fill holes of the figure
#     sil = (pad[1:-1, 1:-1] != 2).astype(np.uint8)
#     return ink & sil, sil


# def load_figure():
#     gray = cv2.imread(IMAGE_PATH, cv2.IMREAD_GRAYSCALE)
#     if gray is None:
#         raise FileNotFoundError(f"'{IMAGE_PATH}' not found. Put the image next to this script.")
#     ink, sil = find_figure(gray)
#     ys, xs = np.nonzero(sil)
#     gray = gray[ys.min():ys.max() + 1, xs.min():xs.max() + 1]   # crop to the figure

#     # Fit to the screen: the quote goes at the top, the figure below it
#     fig_h = H * 0.83
#     scale = min(fig_h / gray.shape[0], (W * 0.9) / gray.shape[1])
#     gray = cv2.resize(gray, (int(gray.shape[1] * scale), int(gray.shape[0] * scale)),
#                       interpolation=cv2.INTER_AREA)
#     ink, sil = find_figure(gray)
#     bh, bw = gray.shape
#     ox, oy = int((W - bw) / 2), int(H * 0.15)
#     return ink, sil, ox, oy, bw, bh


# ink_m, sil_m, ox, oy, bw, bh = load_figure()
# fill_m = sil_m & (1 - ink_m)                                 # figure area without the lines

# iy, ix = np.nonzero(ink_m)                                   # every pixel of every line
# fy_, fx_ = np.nonzero(fill_m)                                # every pixel of the figure's body
# NI, NF = len(ix), len(fx_)

# # Where the tracing starts (the face)
# focus_x = FOCUS_REL[0] * bw
# focus_y = FOCUS_REL[1] * bh

# # ---------------- LINE SEGMENTS ----------------
# # Cut the lines into pieces. The "pen" of each piece runs from its end nearest
# # to the face to its far end; pieces nearer to the face start first.
# n_cc, cc = cv2.connectedComponents(ink_m, connectivity=8)
# CELL = max(8, int(SEG_LEN * 0.7))
# key = cc[iy, ix].astype(np.int64) * 1000000 + (iy // CELL) * 1000 + (ix // CELL)
# _, seg_id = np.unique(key, return_inverse=True)
# NS = seg_id.max() + 1

# dist_ink = np.hypot(ix - focus_x, iy - focus_y).astype(np.float32)
# seg_min = np.full(NS, 1e9, dtype=np.float32)
# seg_max = np.zeros(NS, dtype=np.float32)
# np.minimum.at(seg_min, seg_id, dist_ink)
# np.maximum.at(seg_max, seg_id, dist_ink)
# seg_len = np.maximum(seg_max - seg_min, 6.0)
# seg_dur = np.clip(seg_len / SEG_SPEED, SEG_MIN_DUR, SEG_MAX_DUR)
# seg_t0 = TRACE_START + (seg_min / dist_ink.max()) * TRACE_SPREAD + np.random.uniform(0, 0.35, NS)

# # time at which each line pixel is drawn
# t_ink = (seg_t0[seg_id] + np.clip((dist_ink - seg_min[seg_id]) / seg_len[seg_id], 0, 1)
#          * seg_dur[seg_id]).astype(np.float32)

# # ---------------- FILL ----------------
# XW = 0.8   # <1 makes the fill front flatter (more horizontal)
# fill_dist = np.hypot((fx_ - focus_x) * XW, fy_ - focus_y).astype(np.float32)
# ink_fdist = np.hypot((ix - focus_x) * XW, iy - focus_y).astype(np.float32)
# R_END = float(max(fill_dist.max(), ink_fdist.max())) + SOFT * 1.5 + 40

# # color of the fill: mostly top -> bottom, a little left -> right
# fill_col = palette(0.78 * fy_ / bh + 0.22 * fx_ / bw).astype(np.float32)

# # diagonal coordinate used by the shimmer light sweep (0..1)
# fill_u = ((0.6 * fx_ / bw + 0.8 * fy_ / bh) / 1.4).astype(np.float32)
# ink_u = ((0.6 * ix / bw + 0.8 * iy / bh) / 1.4).astype(np.float32)

# # screen positions
# ix_s, iy_s = (ix + ox).astype(np.int32), (iy + oy).astype(np.int32)
# fx_s, fy_s = (fx_ + ox).astype(np.int32), (fy_ + oy).astype(np.int32)

# # ---------------- SPARKLES ----------------
# spk = np.zeros((TWINKLES, 4), dtype=np.float32)    # x, y, start time, life
# for i in range(TWINKLES):
#     spk[i] = (0, 0, -99, 1)


# def update_sparkles(t):
#     visible = np.nonzero(t_ink < t)[0]
#     if len(visible) == 0:
#         return
#     for i in range(TWINKLES):
#         if t > spk[i, 2] + spk[i, 3]:
#             j = random.choice(visible)
#             spk[i] = (ix_s[j], iy_s[j], t, random.uniform(0.5, 1.2))


# def draw_sparkles(buf, t):
#     for x, y, t0, life in spk:
#         age = t - t0
#         if 0 <= age <= life:
#             b = math.sin(math.pi * age / life) ** 2
#             x, y = int(x), int(y)
#             for dx, dy, k in ((0, 0, 1.0), (1, 0, .55), (-1, 0, .55), (0, 1, .55), (0, -1, .55)):
#                 if 0 <= x + dx < W and 0 <= y + dy < H:
#                     buf[x + dx, y + dy] = (255 * b * k + buf[x + dx, y + dy] * (1 - b * k)).astype(np.uint8)


# # ---------------- TEXT (appears word by word) ----------------
# font = pygame.font.SysFont("georgia,timesnewroman,times,serif", 26, italic=True)
# words = []     # (surface, x, y, start_time)
# lines = QUOTE.split("\n")
# space_w = font.size(" ")[0]
# k_word = 0
# for li, line in enumerate(lines):
#     parts = line.split()
#     surfs = []
#     for wi, w_ in enumerate(parts):
#         c = palette(wi / max(1, len(parts) - 1))
#         s = font.render(w_, True, tuple(int(v) for v in c)).convert_alpha()
#         surfs.append(s)
#     total = sum(s.get_width() for s in surfs) + space_w * (len(surfs) - 1)
#     x = (W - total) / 2
#     y = H * (0.045 + 0.047 * li)
#     for s in surfs:
#         words.append((s, x, y, TEXT_START + k_word * WORD_GAP))
#         x += s.get_width() + space_w
#         k_word += 1

# buf = np.zeros((W, H, 3), dtype=np.uint8)    # pixel buffer, drawn to the screen in one go
# bg = np.array(BG, dtype=np.float32)
# static = None                                # finished picture, cached so the end is cheap


# # ---------------- RENDER ONE FRAME ----------------
# def render(t):
#     buf[:] = BG

#     # fill front: grows from the face outwards
#     prog = min(1.0, max(0.0, (t - FILL_START) / (FILL_END - FILL_START)))
#     R = R_END * ease_in_out(prog) if prog > 0 else -1e6

#     # shimmer: a light band sweeping over the figure
#     s = (t - SHIMMER_START) / SHIMMER_DUR
#     shim_pos = -0.25 + 1.5 * ease_sine(s) if 0 < s < 1 else None

#     # ---- body fill ----
#     if prog > 0:
#         a = np.clip((R - fill_dist) / SOFT, 0.0, 1.0)
#         glow = np.exp(-((fill_dist - R + 10) / 22.0) ** 2) * 0.55 * (1.0 - prog * 0.6)
#         show = (a > 0.004) | (glow > 0.02)
#         col = fill_col[show] * a[show, None] + BAND_COL * (glow[show] * (1 - a[show]))[:, None]
#         if shim_pos is not None:
#             hl = np.exp(-((fill_u[show] - shim_pos) / 0.09) ** 2) * 0.3
#             col = col + 255.0 * hl[:, None]
#         buf[fx_s[show], fy_s[show]] = np.minimum(col, 255).astype(np.uint8)

#     # ---- lines ----
#     seen = t_ink <= t
#     if seen.any():
#         age = t - t_ink[seen]
#         head = np.clip(1.0 - age / 0.35, 0.0, 1.0)[:, None]          # bright tip of the pen
#         col = TRACE_COL + (255.0 - TRACE_COL) * head
#         if prog > 0:
#             ca = np.clip((R - ink_fdist[seen]) / SOFT, 0.0, 1.0)[:, None]
#             col = col * (1 - ca) + INK_DARK * ca                       # lines turn dark once filled
#         if shim_pos is not None:
#             hl = np.exp(-((ink_u[seen] - shim_pos) / 0.09) ** 2) * 0.35
#             col = col + 255.0 * hl[:, None]
#         buf[ix_s[seen], iy_s[seen]] = np.minimum(col, 255).astype(np.uint8)


# # ---------------- MAIN LOOP ----------------
# t = 0.0
# running = True
# while running:
#     dt = clock.tick(FPS) / 1000.0
#     t += dt
#     for e in pygame.event.get():
#         if e.type == pygame.QUIT:
#             running = False
#         if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
#             t = 0.0                                  # press R to restart
#             static = None
#     if t >= DURATION:                                # loop
#         t = 0.0
#         static = None
#         spk[:] = (0, 0, -99, 1)

#     fade = 1.0 - min(1.0, max(0.0, (t - FADE_START) / (DURATION - FADE_START)))

#     if static is not None and fade == 1.0:
#         buf[:] = static                              # finished picture: just copy it
#     else:
#         render(t)
#         if t > SHIMMER_START + SHIMMER_DUR and fade == 1.0:
#             static = buf.copy()

#     if t < FILL_END:
#         update_sparkles(t)
#         draw_sparkles(buf, t)

#     if fade < 1.0:
#         buf[:] = (bg + (buf.astype(np.float32) - bg) * fade).astype(np.uint8)

#     pygame.surfarray.blit_array(screen, buf)

#     # quote: word by word, each word fades in and floats up a little
#     for surf, x, y, t0 in words:
#         if t > t0:
#             al = ease_out(min(1.0, (t - t0) / WORD_DUR))
#             surf.set_alpha(int(255 * al * fade))
#             screen.blit(surf, (x, y + (1 - al) * 10))

#     pygame.display.flip()