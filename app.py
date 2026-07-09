from __future__ import annotations

import io
import math
import os
import random
import colorsys
from hashlib import md5
from typing import Any, Callable

from flask import Flask, Response, render_template, request
from PIL import Image, ImageDraw, ImageFilter, ImageFont

app = Flask(__name__)
PARTICLE_PALETTE = ("#F2C94C", "#F9D976", "#FFFDE7")
PARTICLE_PALETTE_TEAL = ("#4F8B7D", "#5BA89A", "#7BC1AA")


def _clamp_axes(value: Any) -> int:
    try:
        axes = int(value)
    except (TypeError, ValueError):
        axes = 6
    return max(2, min(12, axes))


def _clamp_strength(value: Any) -> float:
    try:
        strength = float(value)
    except (TypeError, ValueError):
        strength = 0.7

    if strength > 1.0:
        strength = strength / 100.0
    return max(0.0, min(1.0, strength))


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _transform_point(x: float, y: float, angle: float, mirrored: bool, center: float) -> tuple[float, float]:
    x0 = x - center
    y0 = y - center
    mx = -x0 if mirrored else x0
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    rx = mx * cos_a - y0 * sin_a
    ry = mx * sin_a + y0 * cos_a
    return rx + center, ry + center



Point = tuple[float, float]
Path = list[Point]


def _normalize_path(path: Path) -> Path:
    return [(_clampf(x, 0.0, 1.0), _clampf(y, 0.0, 1.0)) for x, y in path]


def generate_cloud_flower_path(cx=0.5, cy=0.5, scale=0.4, petals=6, turns=2.5, points=200):
  path = []
  for i in range(points + 1):
    t = i / points
    angle = turns * 2 * math.pi * t
    r_spiral = scale * t
    petal_mod = 0.3 * math.sin(petals * angle) * (t ** 0.8)
    r = r_spiral + scale * petal_mod
    peakness = abs(math.sin(petals * angle))
    angle_perturb = 0.15 * peakness * math.cos(petals * angle) * (t ** 1.5)
    final_angle = angle + angle_perturb
    x = cx + r * math.cos(final_angle)
    y = cy + r * math.sin(final_angle)
    path.append((x, y))
  return path


def generate_spiral_path(cx=0.5, cy=0.5, scale=0.4, turns=3, points=50):
  path: Path = []
  for i in range(points + 1):
    t = i / points
    angle = turns * 2 * math.pi * t
    r = scale * t
    x = cx + r * math.cos(angle)
    y = cy + r * math.sin(angle)
    path.append((x, y))
  return _apply_organic_noise(path, amplitude=0.018, seed=83.0)


def generate_petal_path(cx=0.5, cy=0.5, radius=0.4, inner=0.15, points=50):
  path: Path = []
  petals = 6
  for i in range(points + 1):
    t = i / points
    angle = 2 * math.pi * t
    mod = 0.5 + 0.5 * math.sin(petals * angle)
    r = inner + (radius - inner) * mod
    x = cx + r * math.cos(angle)
    y = cy + r * math.sin(angle)
    path.append((x, y))
  return _apply_organic_noise(path, amplitude=0.017, seed=89.0)


def _noise2d(x: float, y: float, seed: float) -> float:
  n = math.sin((x + seed * 0.17) * 12.73 + (y - seed * 0.11) * 18.91)
  n += 0.5 * math.cos((x - seed * 0.07) * 23.17 - (y + seed * 0.19) * 9.31)
  n += 0.33 * math.sin((x + y + seed * 0.13) * 31.11)
  return n / 1.83


def _apply_organic_noise(path: Path, amplitude: float = 0.016, seed: float | None = None) -> Path:
  if seed is None:
    seed = random.uniform(0.0, 1000.0)
  clean = _normalize_path(path)
  organic: Path = []
  for idx, (x, y) in enumerate(clean):
    n1 = _noise2d(x + idx * 0.009, y - idx * 0.013, seed)
    n2 = _noise2d(x + 3.7, y + 7.9, seed + 1.37)
    w = amplitude * (0.55 + 0.45 * math.sin(idx * 0.21 + seed * 0.03))
    organic.append((_clampf(x + n1 * w, 0.0, 1.0), _clampf(y + n2 * w, 0.0, 1.0)))
  return organic


def motif_yun() -> Path:
    path: Path = []
    turns = 2.8
    steps = 160
    for i in range(steps):
      t = (i / (steps - 1)) * (turns * 2 * math.pi)
      r = 0.02 + 0.18 * (t / (turns * 2 * math.pi))
      x = 0.5 + r * math.cos(t)
      y = 0.5 + r * math.sin(t)
      path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.018, seed=11.0)


def motif_hua() -> Path:
    path: Path = []
    petals = 7
    steps = 220
    for i in range(steps):
      t = (i / (steps - 1)) * (2 * math.pi)
      r = 0.15 + 0.16 * (0.5 + 0.5 * math.sin(petals * t))
      x = 0.5 + r * math.cos(t)
      y = 0.5 + r * math.sin(t)
      path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.017, seed=17.0)


def motif_shui() -> Path:
    path: Path = []
    steps = 120
    for i in range(steps):
      x = 0.1 + 0.8 * (i / (steps - 1))
      y = 0.52 + 0.1 * math.sin(4 * math.pi * i / (steps - 1))
      path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.015, seed=23.0)


def motif_shan() -> Path:
    peaks = [0.12, 0.22, 0.35, 0.47, 0.62, 0.78, 0.9]
    heights = [0.75, 0.45, 0.66, 0.4, 0.7, 0.5, 0.73]
    path: Path = [(0.08, 0.82)]
    for x, y in zip(peaks, heights):
      path.append((x, y))
    path.append((0.94, 0.82))
    return _apply_organic_noise(path, amplitude=0.012, seed=29.0)


def motif_yue() -> Path:
    path: Path = []
    radii = (0.14, 0.19, 0.24)
    for radius in radii:
      steps = 70
      for i in range(steps):
        t = (-0.2 * math.pi) + (1.4 * math.pi * i / (steps - 1))
        x = 0.5 + radius * math.cos(t)
        y = 0.5 + radius * math.sin(t)
        path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.011, seed=31.0)


def motif_feng() -> Path:
    path: Path = []
    phase = random.uniform(0.0, math.pi)
    amp = random.uniform(0.08, 0.13)
    steps = 140
    for i in range(steps):
      t = i / (steps - 1)
      x = 0.08 + 0.84 * t
      y = 0.5 + amp * math.sin(2.5 * math.pi * t + phase) + 0.02 * math.sin(8 * math.pi * t)
      path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.02, seed=37.0)


def motif_xue() -> Path:
    path: Path = []
    center = (0.5, 0.5)
    branches = 6
    for i in range(branches):
      angle = i * (2 * math.pi / branches)
      length = 0.24 + 0.04 * (i % 2)
      tip = (center[0] + length * math.cos(angle), center[1] + length * math.sin(angle))
      path.extend([center, tip])
      for ratio in (0.4, 0.62):
        base_x = center[0] + ratio * length * math.cos(angle)
        base_y = center[1] + ratio * length * math.sin(angle)
        for sign in (-1, 1):
          twig_angle = angle + sign * (math.pi / 5)
          twig_len = 0.07
          twig = (base_x + twig_len * math.cos(twig_angle), base_y + twig_len * math.sin(twig_angle))
          path.extend([(base_x, base_y), twig])
    return _apply_organic_noise(path, amplitude=0.01, seed=41.0)


def motif_liu() -> Path:
    path: Path = []
    steps = 140
    for i in range(steps):
      t = i / (steps - 1)
      x = 0.45 + 0.12 * math.sin(math.pi * t)
      y = 0.14 + 0.72 * t
      path.append((x, y))
    for i in range(steps):
      t = i / (steps - 1)
      x = 0.55 - 0.1 * math.sin(math.pi * t)
      y = 0.14 + 0.72 * t
      path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.014, seed=43.0)


def motif_niao() -> Path:
    path: Path = []
    steps = 80
    for i in range(steps):
      t = i / (steps - 1)
      x = 0.2 + 0.3 * t
      y = 0.56 - 0.1 * math.sin(math.pi * t)
      path.append((x, y))
    for i in range(steps):
      t = i / (steps - 1)
      x = 0.5 + 0.3 * t
      y = 0.56 - 0.1 * math.sin(math.pi * (1 - t))
      path.append((x, y))
    path.extend([(0.49, 0.58), (0.53, 0.62), (0.51, 0.66)])
    return _apply_organic_noise(path, amplitude=0.013, seed=47.0)


def motif_yu() -> Path:
    path: Path = []
    rows = 4
    cols = 6
    for row in range(rows):
      y0 = 0.3 + row * 0.12
      for col in range(cols):
        x0 = 0.18 + col * 0.11 + (0.055 if row % 2 else 0.0)
        steps = 20
        for i in range(steps):
          t = math.pi * (i / (steps - 1))
          x = x0 + 0.045 * math.cos(t)
          y = y0 - 0.04 * math.sin(t)
          path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.012, seed=53.0)


def motif_he() -> Path:
    path: Path = [
      (0.3, 0.7),
      (0.42, 0.56),
      (0.5, 0.5),
      (0.6, 0.44),
      (0.68, 0.3),
      (0.62, 0.22),
      (0.55, 0.28),
      (0.58, 0.4),
      (0.46, 0.54),
      (0.4, 0.76),
      (0.33, 0.84),
      (0.26, 0.8),
    ]
    return _apply_organic_noise(path, amplitude=0.012, seed=59.0)


def motif_song() -> Path:
    path: Path = []
    trunks = [0.38, 0.5, 0.62]
    for x0 in trunks:
      for k in range(12):
        y0 = 0.22 + k * 0.05
        spread = 0.07 + 0.02 * math.sin(k)
        path.extend([(x0, y0), (x0 - spread, y0 + 0.02), (x0, y0), (x0 + spread, y0 + 0.02)])
    return _apply_organic_noise(path, amplitude=0.014, seed=61.0)


def motif_zhu() -> Path:
    path: Path = []
    stems = [0.38, 0.5, 0.62]
    for x0 in stems:
      path.extend([(x0, 0.14), (x0, 0.86)])
      for node in (0.28, 0.44, 0.6, 0.76):
        path.extend([(x0 - 0.03, node), (x0 + 0.03, node)])
    return _apply_organic_noise(path, amplitude=0.009, seed=67.0)


def motif_lou() -> Path:
    tiers = [
      (0.24, 0.72, 0.76, 0.78),
      (0.3, 0.6, 0.7, 0.68),
      (0.36, 0.48, 0.64, 0.56),
      (0.42, 0.36, 0.58, 0.44),
    ]
    path: Path = []
    for x1, y1, x2, y2 in tiers:
      path.extend([(x1, y2), (x2, y2), (x2, y1), (x1, y1), (x1, y2)])
    return _apply_organic_noise(path, amplitude=0.008, seed=71.0)


def motif_zhou() -> Path:
    path: Path = []
    steps = 120
    for i in range(steps):
      t = i / (steps - 1)
      x = 0.18 + 0.64 * t
      y = 0.64 + 0.08 * (4 * (t - 0.5) ** 2 - 1)
      path.append((x, y))
    path.extend([(0.3, 0.6), (0.5, 0.52), (0.7, 0.6)])
    return _apply_organic_noise(path, amplitude=0.013, seed=73.0)


def motif_yu_rain() -> Path:
    """Generate raindrops pattern for rain imagery."""
    path: Path = []
    rows = 6
    cols = 5
    for row in range(rows):
      y0 = 0.15 + row * 0.13
      for col in range(cols):
        x0 = 0.2 + col * 0.15 + (0.075 if row % 2 else 0.0)
        steps = 25
        for i in range(steps):
          t = i / (steps - 1)
          x = x0 + 0.035 * math.cos(t * 2 * math.pi)
          y = y0 + 0.055 * t - 0.025 * math.sin(t * 2 * math.pi)
          path.append((x, y))
    return _apply_organic_noise(path, amplitude=0.011, seed=79.0)


BASE_MOTIF_GENERATORS: dict[str, Callable[[], Path]] = {
  "云花": lambda: _normalize_path(generate_cloud_flower_path()),
  "云": lambda: generate_spiral_path(0.5, 0.5, 0.4, 3, 50),
  "花": lambda: generate_petal_path(0.5, 0.5, 0.4, 0.15, 50),
    "水": motif_shui,
    "山": motif_shan,
    "月": motif_yue,
    "风": motif_feng,
    "雪": motif_xue,
    "柳": motif_liu,
    "鸟": motif_niao,
    "鱼": motif_yu,
    "鹤": motif_he,
    "松": motif_song,
    "竹": motif_zhu,
    "楼": motif_lou,
    "舟": motif_zhou,
    "雨": motif_yu_rain,
  }


def extract_imagery(poem: str) -> list[str]:
    found = [word for word in BASE_MOTIF_GENERATORS if word in poem]
    if found:
      return found
    return random.sample(list(BASE_MOTIF_GENERATORS.keys()), k=2)


def _fuse_pair(path_a: Path, path_b: Path, weight_a: float = 0.6) -> Path:
    sample_count = max(96, len(path_a), len(path_b))
    a_resampled = _resample_evenly(_normalize_path(path_a), sample_count)
    b_resampled = _resample_evenly(_normalize_path(path_b), sample_count)
    weight_b = 1.0 - weight_a

    fused: Path = []
    seed = random.uniform(0.0, 1000.0)
    for idx, (a_pt, b_pt) in enumerate(zip(a_resampled, b_resampled)):
      x = weight_a * a_pt[0] + weight_b * b_pt[0]
      y = weight_a * a_pt[1] + weight_b * b_pt[1]
      px = 0.008 * _noise2d(x + idx * 0.01, y, seed)
      py = 0.008 * _noise2d(x, y + idx * 0.012, seed + 2.1)
      fused.append((_clampf(x + px, 0.0, 1.0), _clampf(y + py, 0.0, 1.0)))
    return fused


def _scatter_near_path(main_path: Path, source_path: Path, count: int = 14) -> list[Path]:
    if len(main_path) < 2 or len(source_path) < 2:
      return []

    anchors = _resample_evenly(main_path, min(max(8, len(main_path) // 8), 28))
    mini_source = _resample_evenly(source_path, max(36, min(100, len(source_path))))

    scatter_paths: list[Path] = []
    for i in range(count):
      anchor = random.choice(anchors)
      theta = random.uniform(0.0, 2 * math.pi)
      radius = random.uniform(0.02, 0.1)
      cx = _clampf(anchor[0] + radius * math.cos(theta), 0.0, 1.0)
      cy = _clampf(anchor[1] + radius * math.sin(theta), 0.0, 1.0)

      scale = random.uniform(0.06, 0.16)
      rot = random.uniform(0.0, 2 * math.pi)
      cos_r = math.cos(rot)
      sin_r = math.sin(rot)

      mini: Path = []
      for j, (mx, my) in enumerate(mini_source):
        lx = (mx - 0.5) * scale
        ly = (my - 0.5) * scale
        ox = lx * cos_r - ly * sin_r
        oy = lx * sin_r + ly * cos_r
        qx = _clampf(cx + ox + 0.003 * _noise2d(mx, my, i * 13.0 + j * 0.1), 0.0, 1.0)
        qy = _clampf(cy + oy + 0.003 * _noise2d(my, mx, i * 17.0 + j * 0.1), 0.0, 1.0)
        mini.append((qx, qy))
      scatter_paths.append(mini)

    return scatter_paths


def generate_fused_motif(imagery_list: list[str]) -> dict[str, Any]:
    valid_imagery = [item for item in imagery_list if item in BASE_MOTIF_GENERATORS]
    if not valid_imagery:
      valid_imagery = random.sample(list(BASE_MOTIF_GENERATORS.keys()), k=2)

    main_path = BASE_MOTIF_GENERATORS[valid_imagery[0]]()
    secondary_path = main_path

    if len(valid_imagery) > 1:
      for idx in range(1, len(valid_imagery)):
        secondary_path = BASE_MOTIF_GENERATORS[valid_imagery[idx]]()
        main_path = _fuse_pair(main_path, secondary_path, weight_a=0.6)
      main_path = _apply_organic_noise(main_path, amplitude=0.01)

    scatter_paths = _scatter_near_path(main_path, secondary_path, count=14) if len(valid_imagery) > 1 else []
    return {"main_path": main_path, "scatter_paths": scatter_paths}


def fuse_motifs(imagery_list: list[str]) -> dict[str, Any]:
    valid_imagery = [item for item in imagery_list if item in BASE_MOTIF_GENERATORS]

    if "云" in valid_imagery and "花" in valid_imagery:
      main_path = _normalize_path(generate_cloud_flower_path())
      other_imagery = [img for img in valid_imagery if img not in ("云", "花", "云花")]
      scatter_paths: list[Path] = []
      for img in other_imagery:
        motif_path = BASE_MOTIF_GENERATORS[img]()
        scatter_paths.append(motif_path)
      return {"main_path": main_path, "scatter_paths": scatter_paths}

    # Special handling: when both mountain and rain are present, enhance rain effect
    if "山" in valid_imagery and "雨" in valid_imagery:
      main_path = BASE_MOTIF_GENERATORS["山"]()
      other_imagery = [img for img in valid_imagery if img not in ("山", "雨")]
      scatter_paths: list[Path] = []
      # Add enhanced rain pattern multiple times for denser rainfall effect
      rain_path = BASE_MOTIF_GENERATORS["雨"]()
      scatter_paths.append(rain_path)
      scatter_paths.append(_apply_organic_noise(rain_path, amplitude=0.008, seed=81.0))
      for img in other_imagery:
        motif_path = BASE_MOTIF_GENERATORS[img]()
        scatter_paths.append(motif_path)
      return {"main_path": main_path, "scatter_paths": scatter_paths}

    return generate_fused_motif(valid_imagery)


def _distance(a: Point, b: Point) -> float:
  dx = b[0] - a[0]
  dy = b[1] - a[1]
  return math.hypot(dx, dy)


def _resample_evenly(points: Path, sample_count: int) -> Path:
  if sample_count <= 1 or len(points) <= 1:
    return points[:]

  cumulative = [0.0]
  for i in range(1, len(points)):
    cumulative.append(cumulative[-1] + _distance(points[i - 1], points[i]))

  total = cumulative[-1]
  if total <= 1e-9:
    return [points[0]] * sample_count

  result: Path = []
  targets = [(total * i) / (sample_count - 1) for i in range(sample_count)]
  seg_idx = 0
  for t in targets:
    while seg_idx < len(cumulative) - 2 and cumulative[seg_idx + 1] < t:
      seg_idx += 1

    left_d = cumulative[seg_idx]
    right_d = cumulative[seg_idx + 1]
    p0 = points[seg_idx]
    p1 = points[seg_idx + 1]
    if right_d - left_d <= 1e-9:
      result.append(p0)
      continue

    ratio = (t - left_d) / (right_d - left_d)
    x = p0[0] + (p1[0] - p0[0]) * ratio
    y = p0[1] + (p1[1] - p0[1]) * ratio
    result.append((x, y))

  return result


def _lerp_point(a: Point, b: Point, t: float) -> Point:
  return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _compute_frames(nodes: Path) -> list[tuple[Point, Point]]:
  frames: list[tuple[Point, Point]] = []
  for i in range(len(nodes)):
    if len(nodes) == 1:
      dx, dy = 1.0, 0.0
    elif i == 0:
      dx = nodes[1][0] - nodes[0][0]
      dy = nodes[1][1] - nodes[0][1]
    elif i == len(nodes) - 1:
      dx = nodes[i][0] - nodes[i - 1][0]
      dy = nodes[i][1] - nodes[i - 1][1]
    else:
      dx = nodes[i + 1][0] - nodes[i - 1][0]
      dy = nodes[i + 1][1] - nodes[i - 1][1]

    norm = math.hypot(dx, dy) or 1.0
    tx, ty = dx / norm, dy / norm
    nx, ny = -ty, tx
    frames.append(((tx, ty), (nx, ny)))
  return frames


def _sample_frame(nodes: Path, frames: list[tuple[Point, Point]], t: float) -> tuple[Point, Point, Point]:
  if not nodes:
    return (0.0, 0.0), (1.0, 0.0), (0.0, 1.0)
  if len(nodes) == 1:
    tangent, normal = frames[0]
    return nodes[0], tangent, normal

  q = _clampf(t, 0.0, 1.0) * (len(nodes) - 1)
  i = int(math.floor(q))
  j = min(i + 1, len(nodes) - 1)
  frac = q - i

  node = _lerp_point(nodes[i], nodes[j], frac)
  tan = _lerp_point(frames[i][0], frames[j][0], frac)
  tnorm = math.hypot(tan[0], tan[1]) or 1.0
  tangent = (tan[0] / tnorm, tan[1] / tnorm)
  normal = (-tangent[1], tangent[0])
  return node, tangent, normal


def _apply_symmetry_to_path(path: Path, axes: int, canvas_size: int) -> list[Path]:
  center = canvas_size / 2
  copies: list[Path] = []
  for axis_idx in range(axes):
    angle = axis_idx * (2 * math.pi / axes)
    for mirrored in (False, True):
      transformed: Path = []
      for x, y in path:
        sx, sy = _transform_point(x, y, angle, mirrored, center)
        transformed.append((sx, sy))
      copies.append(transformed)
  return copies


IMAGERY_LINE_STYLE: dict[str, dict[str, float]] = {
  "云": {"wave": 1.2, "smooth": 0.2},
  "花": {"bloom": 0.18, "wave": 0.8},
  "水": {"wave": 3.2, "wave_freq": 1.1, "drift": 0.8},
  "山": {"jag": 2.0, "jag_freq": 2.0, "thickness": 0.25},
  "月": {"arc": 0.28, "smooth": 0.2},
  "风": {"wave": 1.6, "wave_freq": 1.5, "drift": 1.4},
  "雪": {"scatter": 0.35, "opacity": -0.06},
  "柳": {"droop": 2.1, "wave": 0.6},
  "鸟": {"flutter": 0.9, "drift": 0.7},
  "鱼": {"flutter": 1.2, "wave": 0.7},
  "鹤": {"arc": 0.22, "smooth": 0.14},
  "松": {"jag": 1.0, "thickness": 0.18},
  "竹": {"jag": 0.8, "jag_freq": 1.2, "thickness": -0.08},
  "楼": {"jag": 1.1, "jag_freq": 2.4},
  "舟": {"arc": 0.18, "drift": 0.6},
  "雨": {"droop": 1.8, "wave": 0.4, "drift": 0.6},
}


def _clampf(value: float, low: float, high: float) -> float:
  return max(low, min(high, value))


def _build_line_style(imagery_list: list[str], strength: float = 1.0) -> dict[str, float]:
  base_style: dict[str, float] = {
    "wave": 0.0,
    "wave_freq": 1.8,
    "jag": 0.0,
    "jag_freq": 3.0,
    "drift": 0.0,
    "arc": 0.0,
    "bloom": 0.0,
    "droop": 0.0,
    "flutter": 0.0,
    "thickness": 1.0,
    "opacity": 0.0,
    "scatter": 1.0,
    "smooth": 0.0,
    "phase": 0.0,
  }
  style = dict(base_style)

  valid = [img for img in imagery_list if img in IMAGERY_LINE_STYLE]
  if valid:
    digest = md5("|".join(valid).encode("utf-8")).hexdigest()
    style["phase"] = (int(digest[:8], 16) / 0xFFFFFFFF) * (2 * math.pi)
  else:
    style["phase"] = math.pi * 0.5

  for img in valid:
    cfg = IMAGERY_LINE_STYLE[img]
    style["wave"] += cfg.get("wave", 0.0)
    style["wave_freq"] += cfg.get("wave_freq", 0.0)
    style["jag"] += cfg.get("jag", 0.0)
    style["jag_freq"] += cfg.get("jag_freq", 0.0)
    style["drift"] += cfg.get("drift", 0.0)
    style["arc"] += cfg.get("arc", 0.0)
    style["bloom"] += cfg.get("bloom", 0.0)
    style["droop"] += cfg.get("droop", 0.0)
    style["flutter"] += cfg.get("flutter", 0.0)
    style["thickness"] += cfg.get("thickness", 0.0)
    style["opacity"] += cfg.get("opacity", 0.0)
    style["scatter"] += cfg.get("scatter", 0.0)
    style["smooth"] += cfg.get("smooth", 0.0)

  style["wave"] = _clampf(style["wave"], 0.0, 8.0)
  style["wave_freq"] = _clampf(style["wave_freq"], 0.8, 6.0)
  style["jag"] = _clampf(style["jag"], 0.0, 6.0)
  style["jag_freq"] = _clampf(style["jag_freq"], 1.0, 8.0)
  style["drift"] = _clampf(style["drift"], 0.0, 5.0)
  style["arc"] = _clampf(style["arc"], 0.0, 0.8)
  style["bloom"] = _clampf(style["bloom"], 0.0, 0.7)
  style["droop"] = _clampf(style["droop"], 0.0, 5.0)
  style["flutter"] = _clampf(style["flutter"], 0.0, 3.0)
  style["thickness"] = _clampf(style["thickness"], 0.7, 1.7)
  style["opacity"] = _clampf(style["opacity"], -0.22, 0.22)
  style["scatter"] = _clampf(style["scatter"], 0.7, 1.8)
  style["smooth"] = _clampf(style["smooth"], 0.0, 0.8)

  mix = _clampf(strength, 0.0, 1.0)
  for key in ("wave", "wave_freq", "jag", "jag_freq", "drift", "arc", "bloom", "droop", "flutter", "thickness", "opacity", "scatter", "smooth"):
    style[key] = base_style[key] + (style[key] - base_style[key]) * mix
  return style


def grow_motifs_on_skeleton(
  strokes,
  fused_motif,
  axes,
  imagery_list: list[str] | None = None,
  style_strength: float = 1.0,
  canvas_size=800,
):
  input_canvas = 600.0
  scale_canvas = float(canvas_size) / input_canvas
  safe_axes = max(2, int(axes))
  style = _build_line_style(imagery_list or [], strength=style_strength)

  base_main: Path = fused_motif.get("main_path", []) if isinstance(fused_motif, dict) else []
  base_scatter: list[Path] = fused_motif.get("scatter_paths", []) if isinstance(fused_motif, dict) else []
  if not base_main:
    base_main = _resample_evenly(motif_yun(), 140)

  drawing_instructions: list[dict[str, Any]] = []
  scaled_strokes: list[Path] = []

  for stroke_idx, stroke in enumerate(strokes):
    if not isinstance(stroke, list) or len(stroke) < 2:
      continue

    scaled_stroke: Path = []
    for point in stroke:
      if not isinstance(point, dict):
        continue
      x = _float_or_none(point.get("x"))
      y = _float_or_none(point.get("y"))
      if x is None or y is None:
        continue
      scaled_stroke.append((x * scale_canvas, y * scale_canvas))

    if len(scaled_stroke) < 2:
      continue
    scaled_strokes.append(scaled_stroke)

    node_count = random.randint(20, 40)
    nodes = _resample_evenly(scaled_stroke, node_count)
    frames = _compute_frames(nodes)

    phase = style["phase"] + stroke_idx * 0.31
    ribbon: Path = []
    for u, v in _resample_evenly(_normalize_path(base_main), 180):
      node, tangent, normal = _sample_frame(nodes, frames, u)
      growth = 0.35 + 0.65 * math.sin(math.pi * u)
      bloom = 1.0 + style["bloom"] * math.sin(math.pi * u)
      half_width = (6.0 + 20.0 * growth) * style["thickness"] * bloom
      wave_shift = style["wave"] * math.sin((2 * math.pi * style["wave_freq"] * u) + phase)
      jag_shift = style["jag"] * math.sin((2 * math.pi * style["jag_freq"] * u) + phase * 0.7)
      flutter_shift = style["flutter"] * math.sin((12 * math.pi * u) + (v * 5.0) + phase)
      lateral = (v - 0.5) * 2.0 * half_width + wave_shift + 0.6 * jag_shift + 0.4 * flutter_shift
      along = 2.0 * (v - 0.5) + style["drift"] * math.cos((2 * math.pi * u) + phase * 0.3)
      along += style["arc"] * math.sin(math.pi * u) * (v - 0.5) * 1.8
      px = node[0] + tangent[0] * along + normal[0] * lateral
      py = node[1] + tangent[1] * along + normal[1] * lateral
      py += style["droop"] * (u ** 1.5) * (0.35 + 0.65 * abs(v - 0.5))
      ribbon.append((px, py))

    smooth_factor = style["smooth"]
    if smooth_factor > 0.01 and len(ribbon) >= 3:
      smoothed: Path = [ribbon[0]]
      for i in range(1, len(ribbon) - 1):
        prev_pt = ribbon[i - 1]
        cur_pt = ribbon[i]
        next_pt = ribbon[i + 1]
        avg = ((prev_pt[0] + cur_pt[0] + next_pt[0]) / 3, (prev_pt[1] + cur_pt[1] + next_pt[1]) / 3)
        smoothed.append(_lerp_point(cur_pt, avg, smooth_factor))
      smoothed.append(ribbon[-1])
      ribbon = smoothed

    opacity_shift = style["opacity"]
    main_opacity = [
      _clampf(0.30 + opacity_shift, 0.08, 0.92),
      _clampf(0.50 + opacity_shift, 0.08, 0.92),
      _clampf(0.80 + opacity_shift, 0.08, 0.92),
    ]
    main_width = [
      max(1, int(round(6 * style["thickness"]))),
      max(1, int(round(4 * style["thickness"]))),
      max(1, int(round(2 * style["thickness"]))),
    ]

    for ribbon_copy in _apply_symmetry_to_path(ribbon, safe_axes, canvas_size):
      drawing_instructions.append(
        {
          "kind": "path",
          "part": "main",
          "points": ribbon_copy,
          "color": (0, 0, 0),
          "width_profile": main_width,
          "opacity_profile": main_opacity,
        }
      )

    # Overlay motif signatures directly on the skeleton so imagery shape is more legible.
    signature_source = _resample_evenly(_normalize_path(base_main), 120)
    signature_count = max(2, min(6, int(round(2 + style_strength * 4))))
    signature_span = 0.14 + 0.08 * style_strength
    signature_scale = (11.0 + 10.0 * style["thickness"]) * (0.8 + 0.9 * style_strength)
    motif_opacity = [
      _clampf(0.42 + opacity_shift * 0.7, 0.14, 0.92),
      _clampf(0.64 + opacity_shift * 0.7, 0.14, 0.92),
      _clampf(0.88 + opacity_shift * 0.7, 0.14, 0.96),
    ]
    motif_width = [
      max(2, int(round(4 * style["thickness"]))),
      max(1, int(round(3 * style["thickness"]))),
      max(1, int(round(2 * style["thickness"]))),
    ]

    for sig_idx in range(signature_count):
      t0 = (sig_idx + 1) / (signature_count + 1)
      sig_path: Path = []
      for su, sv in signature_source:
        local_t = _clampf(t0 + (su - 0.5) * signature_span, 0.0, 1.0)
        node, tangent, normal = _sample_frame(nodes, frames, local_t)
        along = (su - 0.5) * signature_scale * (1.2 + 0.45 * style["arc"])
        lateral = (sv - 0.5) * 2.0 * signature_scale
        lateral += 0.35 * style["wave"] * math.sin((2 * math.pi * su * style["wave_freq"]) + phase)
        sx = node[0] + tangent[0] * along + normal[0] * lateral
        sy = node[1] + tangent[1] * along + normal[1] * lateral
        sy += 0.6 * style["droop"] * (local_t ** 1.5)
        sig_path.append((sx, sy))

      for sig_copy in _apply_symmetry_to_path(sig_path, safe_axes, canvas_size):
        drawing_instructions.append(
          {
            "kind": "path",
            "part": "motif",
            "points": sig_copy,
            "color": (0, 0, 0),
            "width_profile": motif_width,
            "opacity_profile": motif_opacity,
          }
        )

    bud_count = int(max(8, min(24, (len(nodes) // 2) * style["scatter"])))
    for _ in range(bud_count):
      bud_source = random.choice(base_scatter) if base_scatter else _resample_evenly(base_main, 70)
      t0 = random.uniform(0.02, 0.98)
      bud_scale = random.uniform(3.0, 9.0) * style["thickness"]
      span = random.uniform(0.03, 0.09)
      bud_path: Path = []

      sampled_bud = _resample_evenly(_normalize_path(bud_source), 60)
      for su, sv in sampled_bud:
        local_t = _clampf(t0 + (su - 0.5) * span, 0.0, 1.0)
        node, tangent, normal = _sample_frame(nodes, frames, local_t)
        lateral = (sv - 0.5) * 2.0 * bud_scale
        along = (su - 0.5) * bud_scale * 0.35
        bx = node[0] + tangent[0] * along + normal[0] * lateral
        by = node[1] + tangent[1] * along + normal[1] * lateral
        bud_path.append((bx, by))

      for bud_copy in _apply_symmetry_to_path(bud_path, safe_axes, canvas_size):
        drawing_instructions.append(
          {
            "kind": "path",
            "part": "scatter",
            "points": bud_copy,
            "color": (0, 0, 0),
            "width_profile": [max(1, int(round(3 * style["thickness"]))), max(1, int(round(2 * style["thickness"]))), 1],
            "opacity_profile": [
              _clampf(0.20 + opacity_shift * 0.8, 0.06, 0.82),
              _clampf(0.35 + opacity_shift * 0.8, 0.06, 0.82),
              _clampf(0.55 + opacity_shift * 0.8, 0.06, 0.82),
            ],
          }
        )

    splat_count = int(max(6, min(18, random.randint(6, 12) * style["scatter"])))
    for _ in range(splat_count):
      t = random.uniform(0.05, 0.95)
      node, _tangent, normal = _sample_frame(nodes, frames, t)
      drift = random.uniform(-18.0, 18.0)
      cx = node[0] + normal[0] * drift
      cy = node[1] + normal[1] * drift
      radius = random.uniform(0.8, 2.2)
      for axis_idx in range(safe_axes):
        angle = axis_idx * (2 * math.pi / safe_axes)
        for mirrored in (False, True):
          sx, sy = _transform_point(cx, cy, angle, mirrored, canvas_size / 2)
          drawing_instructions.append(
            {
              "kind": "splat",
              "part": "splat",
              "center": (sx, sy),
              "radius": radius,
              "color": (0, 0, 0),
              "opacity": random.uniform(0.10, 0.26),
            }
          )

  return drawing_instructions, scaled_strokes


IMAGERY_COLOR_MAP: dict[str, str] = {
  "云": "#7A9CAE",
  "花": "#D96C7A",
  "水": "#5E8C7A",
  "山": "#8B7355",
  "月": "#D4C5A9",
  "风": "#7E9A8B",
  "雪": "#C9D4DE",
  "柳": "#6D8A6A",
  "鸟": "#6F6A73",
  "鱼": "#5A8FA8",
  "鹤": "#B96563",
  "松": "#4E6A4A",
  "竹": "#6E8E57",
  "楼": "#A77E5F",
  "舟": "#7B6D5A",
  "雨": "#4F8B7D",
}


def _hex_to_rgb(color_hex: str) -> tuple[int, int, int]:
  value = color_hex.strip().lstrip("#")
  if len(value) != 6:
    return (122, 156, 174)
  return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _vary_color(base_rgb: tuple[int, int, int], index: int) -> tuple[int, int, int, int]:
  del index
  return (base_rgb[0], base_rgb[1], base_rgb[2], 215)


def _shift_hsv(rgb: tuple[int, int, int], dh: float = 0.0, ds: float = 0.0, dv: float = 0.0) -> tuple[int, int, int]:
  r, g, b = [c / 255.0 for c in rgb]
  h, s, v = colorsys.rgb_to_hsv(r, g, b)
  h = (h + dh) % 1.0
  s = max(0.0, min(1.0, s + ds))
  v = max(0.0, min(1.0, v + dv))
  rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
  return (int(rr * 255), int(gg * 255), int(bb * 255))


def _lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
  tt = max(0.0, min(1.0, t))
  return (
    int(a[0] + (b[0] - a[0]) * tt),
    int(a[1] + (b[1] - a[1]) * tt),
    int(a[2] + (b[2] - a[2]) * tt),
  )


def _draw_dashed_path(draw_obj: ImageDraw.ImageDraw, path: Path, dash: int, gap: int, fill: tuple[int, int, int, int], width: int) -> None:
  if len(path) < 2:
    return
  pattern = max(1, dash + gap)
  sampled = _resample_evenly(path, max(2, len(path) * 3))
  for i in range(1, len(sampled)):
    if (i % pattern) <= dash:
      draw_obj.line((sampled[i - 1], sampled[i]), fill=fill, width=width)


def _draw_gradient_path(
  draw_obj: ImageDraw.ImageDraw,
  path: Path,
  start_rgb: tuple[int, int, int],
  end_rgb: tuple[int, int, int],
  alpha: int,
  width: int,
) -> None:
  if len(path) < 2:
    return
  sampled = _resample_evenly(path, max(24, min(260, len(path) * 2)))
  for seg in range(1, len(sampled)):
    t = seg / (len(sampled) - 1)
    seg_rgb = _lerp_rgb(start_rgb, end_rgb, t)
    draw_obj.line(
      (sampled[seg - 1], sampled[seg]),
      fill=(seg_rgb[0], seg_rgb[1], seg_rgb[2], alpha),
      width=max(1, width),
    )


def _project_normalized_path(
  path: Path,
  center: tuple[float, float],
  scale: float,
  rotation: float,
  offset: tuple[float, float] = (0.0, 0.0),
) -> Path:
  cos_r = math.cos(rotation)
  sin_r = math.sin(rotation)
  projected: Path = []
  for x, y in path:
    lx = (x - 0.5) * scale
    ly = (y - 0.5) * scale
    rx = lx * cos_r - ly * sin_r
    ry = lx * sin_r + ly * cos_r
    projected.append((center[0] + rx + offset[0], center[1] + ry + offset[1]))
  return projected


def _paint_imagery_background(
  background: Image.Image,
  imagery_list: list[str],
  primary_rgb: tuple[int, int, int],
  secondary_rgb: tuple[int, int, int] | None,
  style_strength: float,
) -> None:
  size = background.size[0]
  paper_rgb = (245, 240, 230)
  mix = _clampf(style_strength, 0.0, 1.0)

  top_rgb = _lerp_rgb(paper_rgb, primary_rgb, 0.16 + 0.18 * mix)
  bottom_seed = secondary_rgb if secondary_rgb is not None else _shift_hsv(primary_rgb, dh=0.08, ds=-0.2, dv=0.1)
  bottom_rgb = _lerp_rgb(paper_rgb, bottom_seed, 0.12 + 0.14 * mix)

  grad_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
  grad_draw = ImageDraw.Draw(grad_layer, "RGBA")
  for y in range(size):
    t = y / max(1, size - 1)
    row = _lerp_rgb(top_rgb, bottom_rgb, t)
    grad_draw.line(((0, y), (size, y)), fill=(row[0], row[1], row[2], 255), width=1)

  motif_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
  motif_draw = ImageDraw.Draw(motif_layer, "RGBA")
  center = (size / 2, size / 2)

  valid_imagery = [img for img in imagery_list if img in BASE_MOTIF_GENERATORS]
  motif_imagery = valid_imagery[:2] if valid_imagery else ["云"]
  if len(motif_imagery) == 1 and secondary_rgb is not None:
    motif_imagery.append("花")

  for idx, imagery in enumerate(motif_imagery):
    generator = BASE_MOTIF_GENERATORS.get(imagery)
    if generator is None:
      continue

    source = _resample_evenly(_normalize_path(generator()), 220)
    base_hex = IMAGERY_COLOR_MAP.get(imagery, "#7A9CAE")
    base_rgb = _hex_to_rgb(base_hex)
    paint_rgb = _lerp_rgb(base_rgb, paper_rgb, 0.35)

    scale = size * (0.62 - idx * 0.11 + 0.05 * mix)
    offset_x = (-0.18 if idx == 0 else 0.18) * size
    offset_y = (0.05 if idx == 0 else -0.04) * size
    rotation = (-0.42 if idx == 0 else 0.58) + mix * (0.14 if idx == 0 else -0.12)
    projected = _project_normalized_path(source, center, scale, rotation, (offset_x, offset_y))

    widths = [max(1, int(round(5 + 2 * mix))), max(1, int(round(3 + mix))), 1]
    alphas = [int(28 + 48 * mix), int(42 + 64 * mix), int(70 + 86 * mix)]
    for width_px, alpha in zip(widths, alphas):
      motif_draw.line(projected, fill=(paint_rgb[0], paint_rgb[1], paint_rgb[2], alpha), width=width_px)

  motif_layer = motif_layer.filter(ImageFilter.GaussianBlur(radius=0.9 + 1.1 * mix))
  blended = Image.alpha_composite(grad_layer, motif_layer)
  background.paste(blended, (0, 0))


def _point_angle(center: tuple[float, float], point: Point) -> float:
  angle = math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))
  if angle < 0:
    angle += 360.0
  return angle


def _path_segments_by_sweep(path: Path, center: tuple[float, float], sweep_angle: float) -> list[Path]:
  if len(path) < 2:
    return []

  segments: list[Path] = []
  current: Path = []
  for i in range(1, len(path)):
    p0 = path[i - 1]
    p1 = path[i]
    visible = _point_angle(center, p1) <= sweep_angle
    if visible:
      if not current:
        current = [p0, p1]
      else:
        current.append(p1)
    elif current:
      if len(current) > 1:
        segments.append(current)
      current = []

  if current and len(current) > 1:
    segments.append(current)
  return segments


def _collect_motif_bboxes(drawing_instructions: list[dict[str, Any]]) -> list[tuple[float, float, float, float]]:
  boxes: list[tuple[float, float, float, float]] = []
  for instruction in drawing_instructions:
    if instruction.get("kind") != "path":
      continue
    points = instruction.get("points", [])
    if len(points) < 2:
      continue
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    if max_x - min_x < 1.0 or max_y - min_y < 1.0:
      continue
    boxes.append((min_x, min_y, max_x, max_y))
  return boxes


def generate_particles(motif_bboxes, num=300, palette=None):
  particles: list[dict[str, Any]] = []
  if palette is None:
    palette = PARTICLE_PALETTE
  if not motif_bboxes:
    motif_bboxes = [(320.0, 320.0, 480.0, 480.0)]

  centers = [((b[0] + b[2]) * 0.5, (b[1] + b[3]) * 0.5) for b in motif_bboxes]
  for _ in range(num):
    bbox = random.choice(motif_bboxes)
    cx = random.uniform(bbox[0], bbox[2])
    cy = random.uniform(bbox[1], bbox[3])
    nearest = min(centers, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
    base_angle = math.atan2(cy - nearest[1], cx - nearest[0])
    theta = base_angle + random.uniform(-0.7, 0.7)
    speed = random.uniform(0.4, 2.1)
    max_life = random.randint(20, 40)
    particles.append(
      {
        "x": cx,
        "y": cy,
        "vx": math.cos(theta) * speed,
        "vy": math.sin(theta) * speed,
        "life": max_life,
        "max_life": max_life,
        "size": random.randint(1, 3),
        "color": random.choice(palette),
      }
    )
  return particles


def update_particles(particles):
  alive: list[dict[str, Any]] = []
  for p in particles:
    p["life"] -= 1
    if p["life"] <= 0:
      continue
    p["x"] += p["vx"]
    p["y"] += p["vy"]
    p["vx"] *= 0.98
    p["vy"] *= 0.98
    alive.append(p)
  return alive


def draw_particles(draw_obj: ImageDraw.ImageDraw, particles, canvas):
  del canvas
  for p in particles:
    if p["life"] <= 0:
      continue
    ratio = max(0.0, min(1.0, p["life"] / max(1, p["max_life"])))
    rgb = _hex_to_rgb(p["color"])
    alpha = int(40 + 200 * ratio)
    glow_alpha = int(16 + 88 * ratio)
    # Slightly tighten sparkle radius while preserving velocity/life updates.
    r = float(p["size"]) * 0.82
    draw_obj.ellipse((p["x"] - (r + 1.8), p["y"] - (r + 1.8), p["x"] + (r + 1.8), p["y"] + (r + 1.8)), fill=(rgb[0], rgb[1], rgb[2], glow_alpha))
    draw_obj.ellipse((p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r), fill=(rgb[0], rgb[1], rgb[2], alpha))


def _scale_path(points: Path, center: tuple[float, float], scale: float) -> Path:
  if scale == 1.0:
    return points
  return [
    (
      center[0] + (x - center[0]) * scale,
      center[1] + (y - center[1]) * scale,
    )
    for x, y in points
  ]


def _render_pattern_image(
  size: int,
  axes: int,
  scaled_strokes: list[Path],
  drawing_instructions: list[dict[str, Any]],
  imagery_list: list[str],
  primary_rgb: tuple[int, int, int],
  secondary_rgb: tuple[int, int, int] | None,
  style_strength: float,
  main_rgb: tuple[int, int, int],
  scatter_rgb: tuple[int, int, int],
  main_rgb_2: tuple[int, int, int] | None,
  scatter_rgb_2: tuple[int, int, int] | None,
  reveal_progress: float | None = None,
  particles_state: dict[str, Any] | None = None,
  skeleton_alpha: int = 40,
  color_phase: float = 0.0,
) -> Image.Image:
  phase = color_phase % 1.0
  pulse = math.sin(phase * 2 * math.pi)

  bg_primary = _shift_hsv(primary_rgb, dh=0.01 * pulse, ds=0.03 * pulse, dv=0.05 * pulse)
  bg_secondary = None
  if secondary_rgb is not None:
    bg_secondary = _shift_hsv(secondary_rgb, dh=-0.008 * pulse, ds=0.025 * pulse, dv=0.04 * pulse)

  dyn_main_rgb = _shift_hsv(main_rgb, dh=0.018 * pulse, ds=0.04 * pulse, dv=0.06 * pulse)
  dyn_scatter_rgb = _shift_hsv(scatter_rgb, dh=-0.015 * pulse, ds=0.03 * pulse, dv=0.06 * pulse)
  dyn_main_rgb_2 = _shift_hsv(main_rgb_2, dh=0.014 * pulse, ds=0.03 * pulse, dv=0.05 * pulse) if main_rgb_2 is not None else None
  dyn_scatter_rgb_2 = _shift_hsv(scatter_rgb_2, dh=-0.012 * pulse, ds=0.03 * pulse, dv=0.05 * pulse) if scatter_rgb_2 is not None else None

  center = (size / 2, size / 2)
  background = Image.new("RGBA", (size, size), (245, 240, 230, 255))
  _paint_imagery_background(background, imagery_list, bg_primary, bg_secondary, style_strength)
  draw_bg = ImageDraw.Draw(background, "RGBA")

  step = (2 * math.pi) / axes
  for stroke in scaled_strokes:
    if len(stroke) < 2:
      continue
    for i in range(1, len(stroke)):
      p1 = stroke[i - 1]
      p2 = stroke[i]
      for axis_idx in range(axes):
        angle = axis_idx * step
        for mirrored in (False, True):
          a1 = _transform_point(p1[0], p1[1], angle, mirrored, center[0])
          a2 = _transform_point(p2[0], p2[1], angle, mirrored, center[0])
          _draw_dashed_path(draw_bg, [a1, a2], dash=3, gap=2, fill=(138, 130, 117, skeleton_alpha), width=1)

  overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
  overlay_draw = ImageDraw.Draw(overlay, "RGBA")
  sweep = None if reveal_progress is None else max(0.0, min(360.0, reveal_progress * 360.0))
  growth_scale = 1.0
  if reveal_progress is not None:
    growth_scale = min(1.0, max(0.0, reveal_progress / 0.3))

  new_points: list[Point] = []
  prev_sweep = 0.0
  if particles_state is not None:
    prev_sweep = float(particles_state.get("prev_sweep", 0.0))

  for idx, instruction in enumerate(drawing_instructions):
    kind = instruction.get("kind")
    if kind == "splat":
      center_pt = instruction.get("center")
      if not center_pt:
        continue
      radius = float(instruction.get("radius", 1.2))
      src_opacity = float(instruction.get("opacity", 0.16))
      alpha = int(max(0.08, min(0.35, src_opacity)) * 255)
      if dyn_scatter_rgb_2 is not None:
        blend_t = (idx % 17) / 16
        blended = _lerp_rgb(dyn_scatter_rgb, dyn_scatter_rgb_2, blend_t)
        base = (blended[0], blended[1], blended[2], 215)
      else:
        base = _vary_color(dyn_scatter_rgb, idx)
      overlay_draw.ellipse(
        (
          center_pt[0] - radius,
          center_pt[1] - radius,
          center_pt[0] + radius,
          center_pt[1] + radius,
        ),
        fill=(base[0], base[1], base[2], alpha),
      )
      continue

    if kind != "path":
      continue

    path = instruction.get("points", [])
    if len(path) < 2:
      continue
    path = _scale_path(path, center, growth_scale)

    part = instruction.get("part", "main")
    is_main_like = part in ("main", "motif")
    base_seed = dyn_main_rgb if is_main_like else dyn_scatter_rgb
    base = _vary_color(base_seed, idx)
    widths = instruction.get("width_profile", [6, 4, 2])
    opacities = instruction.get("opacity_profile", [0.30, 0.50, 0.80])

    segments = [path]
    if sweep is not None:
      segments = _path_segments_by_sweep(path, center, sweep)
      if segments:
        for segment in segments:
          for p in segment:
            ang = _point_angle(center, p)
            if prev_sweep < ang <= sweep:
              new_points.append(p)

    for segment in segments:
      if len(segment) < 2:
        continue
      if dyn_main_rgb_2 is not None and dyn_scatter_rgb_2 is not None:
        grad_start = dyn_main_rgb if is_main_like else dyn_scatter_rgb
        grad_end = dyn_main_rgb_2 if is_main_like else dyn_scatter_rgb_2
        for width_px, opacity in zip(widths, opacities):
          alpha = int(max(0.0, min(1.0, float(opacity))) * 255)
          _draw_gradient_path(overlay_draw, segment, grad_start, grad_end, alpha, int(round(width_px)))
      else:
        for width_px, opacity in zip(widths, opacities):
          alpha = int(max(0.0, min(1.0, float(opacity))) * 255)
          overlay_draw.line(segment, fill=(base[0], base[1], base[2], alpha), width=max(1, int(round(width_px))))

  overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.8))
  image = Image.alpha_composite(background, overlay)
  draw_image = ImageDraw.Draw(image, "RGBA")

  # Detect if both mountain and rain are present for special teal particle color
  has_mountain = "山" in imagery_list
  has_rain = "雨" in imagery_list
  particle_palette = PARTICLE_PALETTE_TEAL if (has_mountain and has_rain) else PARTICLE_PALETTE

  if particles_state is not None:
    motif_bboxes = _collect_motif_bboxes(drawing_instructions)
    particles = particles_state.setdefault("particles", [])
    if new_points:
      burst_boxes = [(p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12) for p in random.sample(new_points, k=min(36, len(new_points)))]
      particles.extend(generate_particles(burst_boxes, num=min(80, max(12, len(new_points) // 3)), palette=particle_palette))
    if len(particles) < 180:
      refill = min(120, 180 - len(particles))
      particles.extend(generate_particles(motif_bboxes, num=refill, palette=particle_palette))
    particles_state["particles"] = update_particles(particles)
    particles_state["prev_sweep"] = sweep if sweep is not None else 360.0
    draw_particles(draw_image, particles_state["particles"], size)
  else:
    motif_bboxes = _collect_motif_bboxes(drawing_instructions)
    static_particles = generate_particles(motif_bboxes, num=300, palette=particle_palette)
    static_particles = update_particles(static_particles)
    draw_particles(draw_image, static_particles, size)

  stamp_text = "璇玑诗绘"
  stamp_font = ImageFont.load_default()
  stamp_bbox = draw_image.textbbox((0, 0), stamp_text, font=stamp_font)
  stamp_w = stamp_bbox[2] - stamp_bbox[0]
  stamp_h = stamp_bbox[3] - stamp_bbox[1]
  sx = size - stamp_w - 24
  sy = size - stamp_h - 18
  draw_image.text((sx, sy), stamp_text, fill=(146, 66, 55, 150), font=stamp_font)
  return image


def _finalize_png_response(image: Image.Image) -> Response:
  output = io.BytesIO()
  image.save(output, format="PNG")
  return Response(output.getvalue(), mimetype="image/png")


def _finalize_gif_response(frames: list[Image.Image], duration_ms: int = 70, final_hold_ms: int = 1400) -> Response:
  if not frames:
    return _finalize_png_response(_build_fallback_image("生成过程中发生错误"))

  rgb_frames = [frame.convert("RGB") for frame in frames]
  frame_durations = [max(20, duration_ms)] * len(rgb_frames)
  frame_durations[-1] = max(frame_durations[-1], final_hold_ms)
  output = io.BytesIO()
  rgb_frames[0].save(
    output,
    format="GIF",
    save_all=True,
    append_images=rgb_frames[1:],
    duration=frame_durations,
    optimize=False,
    disposal=2,
  )
  return Response(output.getvalue(), mimetype="image/gif")


def _build_fallback_image(message: str, size: int = 800) -> Image.Image:
  image = Image.new("RGB", (size, size), "#f5f0e6")
  draw = ImageDraw.Draw(image, "RGBA")

  draw.ellipse((90, 90, size - 90, size - 90), outline=(170, 157, 134, 86), width=2)
  draw.ellipse((170, 170, size - 170, size - 170), outline=(170, 157, 134, 64), width=1)

  font = ImageFont.load_default()
  text_bbox = draw.textbbox((0, 0), message, font=font)
  text_w = text_bbox[2] - text_bbox[0]
  text_h = text_bbox[3] - text_bbox[1]
  tx = (size - text_w) / 2
  ty = (size - text_h) / 2

  draw.rounded_rectangle(
    (tx - 16, ty - 10, tx + text_w + 16, ty + text_h + 10),
    radius=10,
    fill=(245, 240, 230, 220),
    outline=(181, 162, 136, 150),
    width=1,
  )
  draw.text((tx, ty), message, fill=(110, 94, 74, 230), font=font)

  stamp_text = "璇玑诗绘"
  stamp_bbox = draw.textbbox((0, 0), stamp_text, font=font)
  stamp_w = stamp_bbox[2] - stamp_bbox[0]
  stamp_h = stamp_bbox[3] - stamp_bbox[1]
  sx = size - stamp_w - 22
  sy = size - stamp_h - 18
  draw.text((sx, sy), stamp_text, fill=(146, 66, 55, 150), font=font)
  return image


@app.get("/")
def index() -> str:
  return render_template("index.html")


@app.post("/generate")
def generate() -> Response:
  try:
    payload = request.get_json(silent=True) or {}
    axes = _clamp_axes(payload.get("axes", 6))
    style_strength = _clamp_strength(payload.get("styleStrength", 0.7))
    animated = _as_bool(payload.get("animated"), default=False)
    try:
      frame_count = int(payload.get("frames", 36))
    except (TypeError, ValueError):
      frame_count = 36
    frame_count = max(12, min(72, frame_count))
    strokes = payload.get("strokes", [])
    poem = str(payload.get("poem", "")).strip()

    if not strokes or not poem:
      fallback = _build_fallback_image("请先书写笔画并输入诗句")
      return _finalize_png_response(fallback)

    imagery_list = extract_imagery(poem)
    fused_motif = fuse_motifs(imagery_list)
    drawing_instructions, scaled_strokes = grow_motifs_on_skeleton(
      strokes,
      fused_motif,
      axes,
      imagery_list=imagery_list,
      style_strength=style_strength,
      canvas_size=800,
    )

    size = 800
    color_imagery = [img for img in imagery_list if img in IMAGERY_COLOR_MAP]
    first_imagery = color_imagery[0] if color_imagery else "云"
    second_imagery = color_imagery[1] if len(color_imagery) > 1 else None

    primary_hex = IMAGERY_COLOR_MAP.get(first_imagery, "#7A9CAE")
    primary_rgb = _hex_to_rgb(primary_hex)
    secondary_rgb = _hex_to_rgb(IMAGERY_COLOR_MAP[second_imagery]) if second_imagery else None

    main_rgb = _shift_hsv(primary_rgb, dh=0.0, ds=-0.05, dv=0.04)
    scatter_rgb = _shift_hsv(primary_rgb, dh=0.03, ds=-0.18, dv=0.10)
    main_rgb_2 = _shift_hsv(secondary_rgb, dh=0.0, ds=-0.05, dv=0.04) if secondary_rgb else None
    scatter_rgb_2 = _shift_hsv(secondary_rgb, dh=0.03, ds=-0.18, dv=0.10) if secondary_rgb else None

    render_kwargs = {
      "size": size,
      "axes": axes,
      "scaled_strokes": scaled_strokes,
      "drawing_instructions": drawing_instructions,
      "imagery_list": imagery_list,
      "primary_rgb": primary_rgb,
      "secondary_rgb": secondary_rgb,
      "style_strength": style_strength,
      "main_rgb": main_rgb,
      "scatter_rgb": scatter_rgb,
      "main_rgb_2": main_rgb_2,
      "scatter_rgb_2": scatter_rgb_2,
    }

    if animated:
      particles_state: dict[str, Any] = {"particles": [], "prev_sweep": 0.0}
      frames: list[Image.Image] = []
      for frame_idx in range(frame_count):
        phase = frame_idx / frame_count
        frame = _render_pattern_image(
          **render_kwargs,
          reveal_progress=None,
          particles_state=particles_state,
          skeleton_alpha=32,
          color_phase=phase,
        )
        frames.append(frame)
      return _finalize_gif_response(frames, duration_ms=70)

    static_image = _render_pattern_image(**render_kwargs)
    return _finalize_png_response(static_image.convert("RGB"))
  except Exception:
    fallback = _build_fallback_image("生成过程中发生错误")
    return _finalize_png_response(fallback)


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  debug_mode = _as_bool(os.environ.get("FLASK_DEBUG"), default=False)
  app.run(host="0.0.0.0", port=port, debug=debug_mode)
