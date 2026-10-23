"""Capture the public SciencePal run at full resolution, headless and reproducibly.

The film's SciencePal scene has to show the real system, not a mock-up, so the frames come from the
same public share link a judge would open:

    https://sciencepal.ai/share/248df9d7-b3aa-4607-8e4c-c4de1a9abc5e

SciencePal serves that link as a replay of the agent run. The script lets the replay finish, then
grabs the moments worth seeing: the task as it was given, the shell commands the agent ran in its
own sandbox, and the files it produced. Nothing is logged in — the page is public — so the capture
can be repeated by anyone.

    python tools/capture_sciencepal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1]
OUT = VIDEO / "captures"
URL = "https://sciencepal.ai/share/248df9d7-b3aa-4607-8e4c-c4de1a9abc5e"
W, H = 1920, 1080


def main() -> int:
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none"])
        page = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1,
                           color_scheme="dark")
        page.goto(URL, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(6_000)

        # the replay opens on a title card; skip it and let the thread settle
        for label in ("Skip to end", "Start Playback"):
            try:
                page.get_by_role("button", name=label).click(timeout=4_000)
                page.wait_for_timeout(6_000)
                break
            except Exception:
                continue
        page.wait_for_timeout(8_000)

        shots = 0
        page.keyboard.press("End")
        page.wait_for_timeout(2_500)
        for i in range(6):
            page.screenshot(path=str(OUT / ("sciencepal_%02d.png" % i)))
            shots += 1
            page.mouse.wheel(0, -900)
            page.wait_for_timeout(1_400)
        br.close()
    print("wrote %d captures to %s" % (shots, OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
