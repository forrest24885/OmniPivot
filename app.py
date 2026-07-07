from __future__ import annotations

import io
import math
import os
import random
import colorsys
from hashlib import md5
from typing import Any, Callable

from flask import Flask, Response, request
from PIL import Image, ImageDraw, ImageFilter, ImageFont

app = Flask(__name__)

HTML_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OmniPivot Symmetry Studio</title>
  <style>
    :root {
      --paper: #f5f0e6;
      --ink: #2f3a2f;
      --jade: #4f6f66;
      --vermillion: #9d4a3f;
      --mist: #d8d1c4;
      --line: #b9ac95;
      --panel: #f9f5ec;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 20% 20%, #efe7d8 0%, #e8dfcf 40%, #e2d6c1 100%);
      display: flex;
      justify-content: center;
      padding: 22px;
    }

    .app-shell {
      width: min(1200px, 100%);
      display: grid;
      grid-template-columns: 1fr minmax(280px, 360px);
      gap: 24px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: 0 8px 20px rgba(63, 53, 37, 0.08);
      padding: 18px;
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }

    label {
      font-size: 14px;
      letter-spacing: 0.04em;
    }

    input[type="range"] {
      accent-color: var(--jade);
      width: 180px;
    }

    .btn {
      border: 1px solid transparent;
      border-radius: 8px;
      padding: 8px 14px;
      cursor: pointer;
      font-size: 14px;
      transition: transform 120ms ease, background-color 120ms ease;
    }

    .btn:active {
      transform: scale(0.98);
    }

    .btn-clear {
      background: #ebe3d3;
      color: var(--ink);
      border-color: #c7b99f;
    }

    .btn-generate {
      background: var(--jade);
      color: #f7f4ed;
      border-color: #3c584f;
    }

    .canvas-wrap {
      display: flex;
      justify-content: center;
      margin-bottom: 16px;
    }

    #drawCanvas {
      width: 600px;
      height: 600px;
      max-width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--paper);
      touch-action: none;
      box-shadow: inset 0 0 0 1px rgba(124, 108, 87, 0.12);
    }

    .poem-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
    }

    #poemInput {
      width: 100%;
      border: 1px solid #cdbfa8;
      border-radius: 8px;
      padding: 10px 12px;
      background: #fffdf8;
      color: var(--ink);
      font-size: 15px;
    }

    .preview-title {
      margin: 0 0 10px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.06em;
    }

    .image-box {
      min-height: 340px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: linear-gradient(180deg, #fbf7ef 0%, #f4eddf 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
    }

    #resultImage {
      max-width: 100%;
      height: auto;
      display: none;
    }

    #placeholder {
      color: #7a6d5b;
      font-size: 14px;
      text-align: center;
      padding: 16px;
      line-height: 1.6;
    }

    .spinner {
      width: 42px;
      height: 42px;
      border: 3px solid #d7cbb8;
      border-top-color: var(--jade);
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
      display: none;
      position: absolute;
    }

    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    .hint {
      margin-top: 10px;
      color: #7f7261;
      font-size: 13px;
      line-height: 1.5;
    }

    @media (max-width: 980px) {
      .app-shell {
        grid-template-columns: 1fr;
      }

      .image-box {
        min-height: 280px;
      }
    }
  </style>
</head>
<body>
  <main class="app-shell">
    <section class="panel">
      <div class="controls">
        <label for="axesSlider">对称轴数: <strong id="axesValue">6</strong></label>
        <input id="axesSlider" type="range" min="2" max="12" value="6" />
        <button id="clearBtn" class="btn btn-clear" type="button">清空</button>
      </div>

      <div class="canvas-wrap">
        <canvas id="drawCanvas" width="600" height="600"></canvas>
      </div>

      <div class="poem-row">
        <input id="poemInput" type="text" placeholder="输入一句中文诗句，例如：山色空蒙雨亦奇" maxlength="60" />
        <button id="generateBtn" class="btn btn-generate" type="button">Generate Pattern</button>
      </div>
      <p class="hint">按住并拖动画布开始创作，支持鼠标和触控。</p>
    </section>

    <aside class="panel">
      <h2 class="preview-title">生成结果</h2>
      <div class="image-box">
        <div id="spinner" class="spinner"></div>
        <img id="resultImage" alt="生成的对称图案" />
        <div id="placeholder">点击“Generate Pattern”后，
          图案会在这里出现。</div>
      </div>
    </aside>
  </main>

  <script>
    const canvas = document.getElementById('drawCanvas');
    const ctx = canvas.getContext('2d');
    const axesSlider = document.getElementById('axesSlider');
    const axesValue = document.getElementById('axesValue');
    const clearBtn = document.getElementById('clearBtn');
    const poemInput = document.getElementById('poemInput');
    const generateBtn = document.getElementById('generateBtn');
    const resultImage = document.getElementById('resultImage');
    const placeholder = document.getElementById('placeholder');
    const spinner = document.getElementById('spinner');

    const center = { x: canvas.width / 2, y: canvas.height / 2 };

    let drawing = false;
    let currentStroke = [];
    let strokes = [];

    function setBrushStyle() {
      ctx.lineWidth = 1.6;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = '#2f3a2f';
      ctx.globalAlpha = 0.95;
    }

    function getAxes() {
      return Number.parseInt(axesSlider.value, 10) || 6;
    }

    function toCanvasPoint(event) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (event.clientX - rect.left) * scaleX,
        y: (event.clientY - rect.top) * scaleY
      };
    }

    function rotateMirrorPoint(point, angle, mirrored) {
      const x0 = point.x - center.x;
      const y0 = point.y - center.y;
      const mx = mirrored ? -x0 : x0;
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      const rx = mx * cosA - y0 * sinA;
      const ry = mx * sinA + y0 * cosA;
      return { x: rx + center.x, y: ry + center.y };
    }

    function drawSymmetricSegment(p1, p2) {
      const axes = getAxes();
      const unit = (Math.PI * 2) / axes;

      setBrushStyle();
      for (let i = 0; i < axes; i += 1) {
        const angle = unit * i;
        for (const mirrored of [false, true]) {
          const a = rotateMirrorPoint(p1, angle, mirrored);
          const b = rotateMirrorPoint(p2, angle, mirrored);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    function startStroke(event) {
      event.preventDefault();
      drawing = true;
      currentStroke = [];
      const p = toCanvasPoint(event);
      currentStroke.push(p);
      canvas.setPointerCapture(event.pointerId);
    }

    function moveStroke(event) {
      if (!drawing) return;
      event.preventDefault();
      const p = toCanvasPoint(event);
      const prev = currentStroke[currentStroke.length - 1];
      currentStroke.push(p);
      drawSymmetricSegment(prev, p);
    }

    function endStroke(event) {
      if (!drawing) return;
      drawing = false;
      if (currentStroke.length > 0) {
        const normalized = currentStroke.map((p) => ({ x: Number(p.x.toFixed(2)), y: Number(p.y.toFixed(2)) }));
        strokes.push(normalized);
      }
      currentStroke = [];
      if (event.pointerId !== undefined) {
        try {
          canvas.releasePointerCapture(event.pointerId);
        } catch (e) {
          // Ignore release errors when capture is already gone.
        }
      }
    }

    function clearCanvas() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      strokes = [];
      currentStroke = [];
      resultImage.style.display = 'none';
      placeholder.style.display = 'block';
    }

    async function generatePattern() {
      const payload = {
        strokes,
        poem: poemInput.value.trim(),
        axes: getAxes()
      };

      spinner.style.display = 'block';
      placeholder.style.display = 'none';
      generateBtn.disabled = true;

      try {
        const response = await fetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          throw new Error('生成失败，请重试。');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        resultImage.src = url;
        resultImage.style.display = 'block';
      } catch (err) {
        placeholder.textContent = err.message || '网络错误，请稍后再试。';
        placeholder.style.display = 'block';
      } finally {
        spinner.style.display = 'none';
        generateBtn.disabled = false;
      }
    }

    axesSlider.addEventListener('input', () => {
      axesValue.textContent = axesSlider.value;
    });

    clearBtn.addEventListener('click', clearCanvas);
    generateBtn.addEventListener('click', generatePattern);

    canvas.addEventListener('pointerdown', startStroke);
    canvas.addEventListener('pointermove', moveStroke);
    canvas.addEventListener('pointerup', endStroke);
    canvas.addEventListener('pointercancel', endStroke);
    canvas.addEventListener('pointerleave', endStroke);
  </script>
</body>
</html>
"""


def _clamp_axes(value: Any) -> int:
    try:
        axes = int(value)
    except (TypeError, ValueError):
        axes = 6
    return max(2, min(12, axes))


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


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


Point = tuple[float, float]
Path = list[Point]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_path(path: Path) -> Path:
    return [(_clamp01(x), _clamp01(y)) for x, y in path]


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
    organic.append((_clamp01(x + n1 * w), _clamp01(y + n2 * w)))
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
  }

# Compatibility alias for prompt-style naming.
IMAGERY_MAP = BASE_MOTIF_GENERATORS


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
      fused.append((_clamp01(x + px), _clamp01(y + py)))
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
      cx = _clamp01(anchor[0] + radius * math.cos(theta))
      cy = _clamp01(anchor[1] + radius * math.sin(theta))

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
        qx = _clamp01(cx + ox + 0.003 * _noise2d(mx, my, i * 13.0 + j * 0.1))
        qy = _clamp01(cy + oy + 0.003 * _noise2d(my, mx, i * 17.0 + j * 0.1))
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
    valid_imagery = [item for item in imagery_list if item in IMAGERY_MAP]

    if "云" in valid_imagery and "花" in valid_imagery:
      main_path = _normalize_path(generate_cloud_flower_path())
      other_imagery = [img for img in valid_imagery if img not in ("云", "花", "云花")]
      scatter_paths: list[Path] = []
      for img in other_imagery:
        motif_path = IMAGERY_MAP[img]()
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


def _tangent_angle(sampled_points: Path, index: int) -> float:
  if not sampled_points:
    return 0.0

  if index < len(sampled_points) - 1:
    p0 = sampled_points[index]
    p1 = sampled_points[index + 1]
  elif len(sampled_points) >= 2:
    p0 = sampled_points[index - 1]
    p1 = sampled_points[index]
  else:
    return 0.0

  dx = p1[0] - p0[0]
  dy = p1[1] - p0[1]
  if abs(dx) < 1e-9 and abs(dy) < 1e-9:
    return 0.0
  return math.atan2(dy, dx)


def _transform_points_linear(points: Path, matrix: tuple[tuple[float, float], tuple[float, float]], tx: float, ty: float) -> Path:
  transformed: Path = []
  for x, y in points:
    nx = matrix[0][0] * x + matrix[0][1] * y + tx
    ny = matrix[1][0] * x + matrix[1][1] * y + ty
    transformed.append((nx, ny))
  return transformed


def _lerp_point(a: Point, b: Point, t: float) -> Point:
  return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _sample_polyline(path: Path, t: float) -> Point:
  if not path:
    return (0.0, 0.0)
  if len(path) == 1:
    return path[0]
  q = _clamp01(t) * (len(path) - 1)
  i = int(math.floor(q))
  j = min(i + 1, len(path) - 1)
  frac = q - i
  return _lerp_point(path[i], path[j], frac)


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

  q = _clamp01(t) * (len(nodes) - 1)
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


def grow_motifs_on_skeleton(strokes, fused_motif, axes, canvas_size=800):
  input_canvas = 600.0
  scale_canvas = float(canvas_size) / input_canvas
  safe_axes = max(2, int(axes))

  base_main: Path = fused_motif.get("main_path", []) if isinstance(fused_motif, dict) else []
  base_scatter: list[Path] = fused_motif.get("scatter_paths", []) if isinstance(fused_motif, dict) else []
  if not base_main:
    base_main = _resample_evenly(motif_yun(), 140)

  drawing_instructions: list[dict[str, Any]] = []
  scaled_strokes: list[Path] = []

  for stroke in strokes:
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

    ribbon: Path = []
    for u, v in _resample_evenly(_normalize_path(base_main), 180):
      node, tangent, normal = _sample_frame(nodes, frames, u)
      growth = 0.35 + 0.65 * math.sin(math.pi * u)
      half_width = 6.0 + 20.0 * growth
      lateral = (v - 0.5) * 2.0 * half_width
      along = 2.0 * (v - 0.5)
      px = node[0] + tangent[0] * along + normal[0] * lateral
      py = node[1] + tangent[1] * along + normal[1] * lateral
      ribbon.append((px, py))

    for ribbon_copy in _apply_symmetry_to_path(ribbon, safe_axes, canvas_size):
      drawing_instructions.append(
        {
          "kind": "path",
          "part": "main",
          "points": ribbon_copy,
          "color": (0, 0, 0),
          "width_profile": [6, 4, 2],
          "opacity_profile": [0.30, 0.50, 0.80],
        }
      )

    bud_count = max(8, min(20, len(nodes) // 2))
    for _ in range(bud_count):
      bud_source = random.choice(base_scatter) if base_scatter else _resample_evenly(base_main, 70)
      t0 = random.uniform(0.02, 0.98)
      bud_scale = random.uniform(3.0, 9.0)
      span = random.uniform(0.03, 0.09)
      bud_path: Path = []

      sampled_bud = _resample_evenly(_normalize_path(bud_source), 60)
      for su, sv in sampled_bud:
        local_t = _clamp01(t0 + (su - 0.5) * span)
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
            "width_profile": [3, 2, 1],
            "opacity_profile": [0.20, 0.35, 0.55],
          }
        )

    splat_count = random.randint(6, 12)
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
}


def _hex_to_rgb(color_hex: str) -> tuple[int, int, int]:
  value = color_hex.strip().lstrip("#")
  if len(value) != 6:
    return (122, 156, 174)
  return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _vary_color(base_rgb: tuple[int, int, int], index: int) -> tuple[int, int, int, int]:
  shift = int(18 * math.sin(index * 0.83) + 10 * math.cos(index * 0.31))
  r = max(0, min(255, base_rgb[0] + shift))
  g = max(0, min(255, base_rgb[1] + int(shift * 0.7)))
  b = max(0, min(255, base_rgb[2] - int(shift * 0.4)))
  return (r, g, b, 215)


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


_STAMP_SPACING_PX: float = 50.0
_MIN_STAMP_SIZE: float = 5.0
_MAX_STAMP_SIZE: float = 10.0
_MIN_STAMP_ALPHA: int = 150
_MAX_STAMP_ALPHA: int = 210


def _petal_polygon(
  cx: float, cy: float, length: float, width: float, angle: float
) -> list[tuple[float, float]]:
  """Return polygon points for one narrow-ellipse petal centred at (cx, cy) pointing in direction angle."""
  cos_a = math.cos(angle)
  sin_a = math.sin(angle)
  ex = cx + cos_a * length * 0.45
  ey = cy + sin_a * length * 0.45
  pts: list[tuple[float, float]] = []
  for i in range(12):
    t = 2 * math.pi * i / 12
    u = math.cos(t) * length * 0.5
    v = math.sin(t) * width * 0.45
    pts.append((ex + cos_a * u - sin_a * v, ey + sin_a * u + cos_a * v))
  return pts


def _draw_stamp(
  draw_obj: ImageDraw.ImageDraw,
  imagery: str,
  cx: float,
  cy: float,
  size: float,
  angle: float,
  fill: tuple[int, int, int, int],
) -> None:
  """Draw a small imagery-specific decorative motif at pixel position (cx, cy)."""
  a_val = fill[3]
  if imagery in ("花", "云花"):
    # 5-petal flower
    for i in range(5):
      pa = angle + i * (2 * math.pi / 5)
      draw_obj.polygon(_petal_polygon(cx, cy, size * 1.1, size * 0.38, pa), fill=fill)
    cr = max(1.0, size * 0.22)
    draw_obj.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 245, 180, a_val))
  elif imagery == "月":
    # Crescent polygon: back semicircle of outer circle + reversed same arc on shifted inner circle
    outer_r = size
    inner_r = size * 0.72
    inner_off = size * 0.32
    face = angle
    pts_m: list[tuple[float, float]] = []
    for i in range(13):
      a = face + math.pi / 2 + math.pi * i / 12
      pts_m.append((cx + outer_r * math.cos(a), cy + outer_r * math.sin(a)))
    icx = cx + inner_off * math.cos(face)
    icy = cy + inner_off * math.sin(face)
    for i in range(12, -1, -1):
      a = face + math.pi / 2 + math.pi * i / 12
      pts_m.append((icx + inner_r * math.cos(a), icy + inner_r * math.sin(a)))
    draw_obj.polygon(pts_m, fill=fill)
  elif imagery == "山":
    # Two overlapping mountain triangles
    cos_a2 = math.cos(angle)
    sin_a2 = math.sin(angle)
    cos_p = math.cos(angle + math.pi / 2)
    sin_p = math.sin(angle + math.pi / 2)
    for k, (h, w2) in enumerate([(size * 1.1, size * 0.75), (size * 0.72, size * 0.52)]):
      offset_w = (k - 0.5) * size * 0.75
      bx = cx + cos_p * offset_w
      by = cy + sin_p * offset_w
      tip = (bx + cos_a2 * h, by + sin_a2 * h)
      bl = (bx - cos_p * w2, by - sin_p * w2)
      br = (bx + cos_p * w2, by + sin_p * w2)
      draw_obj.polygon([tip, bl, br], fill=(fill[0], fill[1], fill[2], max(0, fill[3] - k * 28)))
  elif imagery == "雪":
    # 6-arm snowflake with small side branches
    arm_len = size * 1.1
    arm_w = max(1, int(size * 0.14))
    branch_len = arm_len * 0.35
    for i in range(6):
      arm_a = angle + i * math.pi / 3
      ex2 = cx + math.cos(arm_a) * arm_len
      ey2 = cy + math.sin(arm_a) * arm_len
      draw_obj.line([(cx, cy), (ex2, ey2)], fill=fill, width=arm_w)
      mid_x = cx + math.cos(arm_a) * arm_len * 0.55
      mid_y = cy + math.sin(arm_a) * arm_len * 0.55
      for delta in (-math.pi / 5, math.pi / 5):
        ba = arm_a + delta
        draw_obj.line(
          [(mid_x, mid_y), (mid_x + math.cos(ba) * branch_len, mid_y + math.sin(ba) * branch_len)],
          fill=fill, width=arm_w,
        )
  elif imagery in ("云", "风"):
    # 3 overlapping puffs
    puff_r = size * 0.55
    for i in range(3):
      pa = angle + i * (2 * math.pi / 3)
      ocx = cx + math.cos(pa) * size * 0.42
      ocy = cy + math.sin(pa) * size * 0.42
      draw_obj.ellipse([ocx - puff_r, ocy - puff_r, ocx + puff_r, ocy + puff_r], fill=fill)
  elif imagery in ("水", "柳"):
    # Wavy line
    cos_a3 = math.cos(angle)
    sin_a3 = math.sin(angle)
    wave_pts: list[tuple[float, float]] = []
    for i in range(15):
      t3 = i / 14
      lx = (t3 - 0.5) * size * 2.6
      ly = math.sin(t3 * 2 * math.pi) * size * 0.42
      wave_pts.append((cx + cos_a3 * lx - sin_a3 * ly, cy + sin_a3 * lx + cos_a3 * ly))
    line_w = max(1, int(size * 0.18))
    for i in range(1, len(wave_pts)):
      draw_obj.line([wave_pts[i - 1], wave_pts[i]], fill=fill, width=line_w)
  else:
    # Generic: 4-petal cross
    for i in range(4):
      pa2 = angle + i * (math.pi / 2)
      draw_obj.polygon(_petal_polygon(cx, cy, size, size * 0.35, pa2), fill=fill)


def _generate_stamp_instructions(
  scaled_strokes: list[Path],
  imagery_list: list[str],
  axes: int,
  canvas_size: int,
) -> list[dict[str, Any]]:
  """Return imagery_stamp instructions placed at regular intervals along each stroke."""
  if not imagery_list or not scaled_strokes:
    return []
  safe_axes = max(2, int(axes))
  instructions: list[dict[str, Any]] = []
  stamp_spacing = _STAMP_SPACING_PX

  for stroke in scaled_strokes:
    if len(stroke) < 2:
      continue
    total_len = sum(_distance(stroke[i], stroke[i + 1]) for i in range(len(stroke) - 1))
    stamp_count = max(2, int(total_len / stamp_spacing))
    nodes = _resample_evenly(stroke, max(stamp_count * 5, 24))
    frames = _compute_frames(nodes)
    for j in range(stamp_count):
      t = (j + 0.5) / stamp_count
      node, tangent, _normal = _sample_frame(nodes, frames, t)
      tang_angle = math.atan2(tangent[1], tangent[0])
      img_type = imagery_list[j % len(imagery_list)]
      stamp_size = random.uniform(_MIN_STAMP_SIZE, _MAX_STAMP_SIZE)
      for axis_idx in range(safe_axes):
        rot = axis_idx * (2 * math.pi / safe_axes)
        for mirrored in (False, True):
          sx, sy = _transform_point(node[0], node[1], rot, mirrored, canvas_size / 2)
          stamp_a = tang_angle + rot + (math.pi if mirrored else 0.0)
          instructions.append({
            "kind": "imagery_stamp",
            "imagery": img_type,
            "center": (sx, sy),
            "size": stamp_size,
            "angle": stamp_a,
          })
  return instructions


def _finalize_png_response(image: Image.Image) -> Response:
  output = io.BytesIO()
  image.save(output, format="PNG")
  return Response(output.getvalue(), mimetype="image/png")


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
    return HTML_PAGE


@app.post("/generate")
def generate() -> Response:
  try:
    payload = request.get_json(silent=True) or {}
    axes = _clamp_axes(payload.get("axes", 6))
    strokes = payload.get("strokes", [])
    poem = str(payload.get("poem", "")).strip()

    if not strokes or not poem:
      fallback = _build_fallback_image("请先书写笔画并输入诗句")
      return _finalize_png_response(fallback)

    imagery_list = extract_imagery(poem)
    fused_motif = fuse_motifs(imagery_list)
    drawing_instructions, scaled_strokes = grow_motifs_on_skeleton(strokes, fused_motif, axes, canvas_size=800)

    size = 800
    center = size / 2
    stamp_instructions = _generate_stamp_instructions(scaled_strokes, imagery_list, axes, size)
    drawing_instructions.extend(stamp_instructions)
    background = Image.new("RGBA", (size, size), (245, 240, 230, 255))
    draw = ImageDraw.Draw(background, "RGBA")

    first_imagery = imagery_list[0] if imagery_list else "云"
    primary_hex = IMAGERY_COLOR_MAP.get(first_imagery, "#7A9CAE")
    primary_rgb = _hex_to_rgb(primary_hex)
    cloud_flower_blend = ("云" in imagery_list and "花" in imagery_list) or ("云花" in imagery_list)

    # Draw faint skeleton lines with subtle dashes.
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
            a1 = _transform_point(p1[0], p1[1], angle, mirrored, center)
            a2 = _transform_point(p2[0], p2[1], angle, mirrored, center)
            _draw_dashed_path(draw, [a1, a2], dash=3, gap=2, fill=(120, 110, 100, 40), width=1)

    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")

    main_rgb = _shift_hsv(primary_rgb, dh=0.0, ds=-0.05, dv=0.04)
    scatter_rgb = _shift_hsv(primary_rgb, dh=0.03, ds=-0.18, dv=0.10)
    cloud_rgb = _hex_to_rgb(IMAGERY_COLOR_MAP.get("云", "#7A9CAE"))
    flower_rgb = _hex_to_rgb(IMAGERY_COLOR_MAP.get("花", "#D96C7A"))
    wisteria_rgb = _hex_to_rgb("#c5a3b4")

    for idx, instruction in enumerate(drawing_instructions):
      kind = instruction.get("kind")
      if kind == "path":
        path = instruction.get("points", [])
        if len(path) < 2:
          continue
        part = instruction.get("part", "main")
        base_seed = main_rgb if part == "main" else scatter_rgb
        base = _vary_color(base_seed, idx)
        widths = instruction.get("width_profile", [6, 4, 2])
        opacities = instruction.get("opacity_profile", [0.30, 0.50, 0.80])
        if cloud_flower_blend and part == "main":
          sampled = _resample_evenly(path, max(30, min(220, len(path) * 2)))
          for width_px, opacity in zip(widths, opacities):
            alpha = int(max(0.0, min(1.0, float(opacity))) * 255)
            width_int = max(1, int(round(width_px)))
            for seg in range(1, len(sampled)):
              t = seg / (len(sampled) - 1)
              if t <= 0.5:
                seg_rgb = _lerp_rgb(flower_rgb, wisteria_rgb, t / 0.5)
              else:
                seg_rgb = _lerp_rgb(wisteria_rgb, cloud_rgb, (t - 0.5) / 0.5)
              overlay_draw.line((sampled[seg - 1], sampled[seg]), fill=(seg_rgb[0], seg_rgb[1], seg_rgb[2], alpha), width=width_int)
        else:
          for width_px, opacity in zip(widths, opacities):
            alpha = int(max(0.0, min(1.0, float(opacity))) * 255)
            overlay_draw.line(path, fill=(base[0], base[1], base[2], alpha), width=max(1, int(round(width_px))))
      elif kind == "splat":
        center_pt = instruction.get("center")
        if not center_pt:
          continue
        radius = float(instruction.get("radius", 1.2))
        src_opacity = float(instruction.get("opacity", 0.16))
        random_alpha = max(0.08, min(0.35, src_opacity * random.uniform(0.8, 1.35)))
        alpha = int(random_alpha * 255)
        base = _vary_color(scatter_rgb, idx)
        overlay_draw.ellipse(
          (
            center_pt[0] - radius,
            center_pt[1] - radius,
            center_pt[0] + radius,
            center_pt[1] + radius,
          ),
          fill=(base[0], base[1], base[2], alpha),
        )
      elif kind == "imagery_stamp":
        center_pt = instruction.get("center")
        if not center_pt:
          continue
        img_type = str(instruction.get("imagery", first_imagery))
        stamp_size = float(instruction.get("size", 7.0))
        stamp_angle = float(instruction.get("angle", 0.0))
        stamp_hex = IMAGERY_COLOR_MAP.get(img_type, primary_hex)
        stamp_rgb = _hex_to_rgb(stamp_hex)
        stamp_alpha = random.randint(_MIN_STAMP_ALPHA, _MAX_STAMP_ALPHA)
        _draw_stamp(
          overlay_draw,
          img_type,
          center_pt[0],
          center_pt[1],
          stamp_size,
          stamp_angle,
          (stamp_rgb[0], stamp_rgb[1], stamp_rgb[2], stamp_alpha),
        )

    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.8))
    image = Image.alpha_composite(background, overlay)
    draw = ImageDraw.Draw(image, "RGBA")

    stamp_text = "璇玑诗绘"
    stamp_font = ImageFont.load_default()
    stamp_bbox = draw.textbbox((0, 0), stamp_text, font=stamp_font)
    stamp_w = stamp_bbox[2] - stamp_bbox[0]
    stamp_h = stamp_bbox[3] - stamp_bbox[1]
    sx = size - stamp_w - 24
    sy = size - stamp_h - 18
    draw.text((sx, sy), stamp_text, fill=(146, 66, 55, 150), font=stamp_font)

    return _finalize_png_response(image.convert("RGB"))
  except Exception:
    fallback = _build_fallback_image("生成过程中发生错误")
    return _finalize_png_response(fallback)


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port, debug=True)
