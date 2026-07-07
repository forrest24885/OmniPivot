#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib import error, request


def build_sample_strokes() -> list[list[dict[str, float]]]:
    # A simple curve-like stroke in the same 600x600 coordinate space as the frontend.
    stroke = []
    for i in range(80):
        t = i / 79
        x = 80 + 440 * t
        y = 320 + 110 * (t - 0.5) ** 2 - 40
        stroke.append({"x": round(x, 2), "y": round(y, 2)})
    return [stroke]


def load_strokes(strokes_file: str | None) -> list[list[dict[str, float]]]:
    if not strokes_file:
        return build_sample_strokes()

    p = Path(strokes_file)
    if not p.exists():
        raise FileNotFoundError(f"Strokes file not found: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Strokes JSON must be a list of strokes.")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call /generate and save returned PNG to local disk.")
    parser.add_argument("--url", default="http://127.0.0.1:5000/generate", help="Generate endpoint URL")
    parser.add_argument("--poem", default="云想衣裳花想容", help="Poem text")
    parser.add_argument("--axes", type=int, default=6, help="Symmetry axes (2-12 recommended)")
    parser.add_argument("--strokes-file", help="Path to strokes JSON file")
    parser.add_argument("--output", help="Output PNG path, e.g. output/result.png")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        strokes = load_strokes(args.strokes_file)
    except Exception as exc:
        print(f"[error] failed to load strokes: {exc}", file=sys.stderr)
        return 1

    payload = {
        "strokes": strokes,
        "poem": args.poem,
        "axes": int(args.axes),
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        args.url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as resp:
            png_data = resp.read()
            status = resp.status
    except error.HTTPError as exc:
        print(f"[error] server returned HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[error] request failed: {exc}", file=sys.stderr)
        return 2

    if status != 200:
        print(f"[error] unexpected response status: {status}", file=sys.stderr)
        return 3

    output_path = Path(args.output) if args.output else Path(
        f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(png_data)

    print(f"[ok] saved generated image: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
