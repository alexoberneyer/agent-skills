#!/usr/bin/env python3
"""Screenshot a deck's slides with headless Chrome, for one look before publishing.

    shot.py DECK OUTDIR [SLIDE ...]      default: every slide

Writes OUTDIR/slide-N.png at 1600x900. Read the PNGs, fix what they show in one
pass, then stop looking.

Needs Chrome or Chromium. Set CHROME to its path if it is somewhere unusual.
"""
import os
import pathlib
import shutil
import subprocess
import sys

CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)


def chrome():
    override = os.environ.get("CHROME")
    if override:
        return override
    for c in CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit("shot.py: no Chrome or Chromium found; set CHROME to its path")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    deck = pathlib.Path(sys.argv[1]).resolve()
    outdir = pathlib.Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    total = deck.read_text(encoding="utf-8").count('<section class="slide')
    slides = [int(s) for s in sys.argv[3:]] or list(range(1, total + 1))
    exe = chrome()
    for n in slides:
        out = outdir / ("slide-%d.png" % n)
        url = deck.as_uri() + ("#s%d" % n if n > 1 else "")
        r = subprocess.run(
            [exe, "--headless", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1", "--virtual-time-budget=4000",
             "--window-size=1600,900", "--screenshot=%s" % out, url],
            capture_output=True, text=True,
        )
        print("slide %d: %s" % (n, out if r.returncode == 0 else "failed (%d)" % r.returncode))


if __name__ == "__main__":
    main()
