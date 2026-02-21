from __future__ import annotations

from pathlib import Path

import cv2


def apply_text_watermark(input_image: str | Path, output_image: str | Path, text: str) -> str | None:
    src = Path(input_image)
    if not src.exists():
        return None

    img = cv2.imread(str(src))
    if img is None:
        return None

    h, w = img.shape[:2]
    out = img.copy()

    # Semi-transparent banner for readability.
    overlay = out.copy()
    cv2.rectangle(overlay, (0, h - 60), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, out, 0.55, 0, out)

    cv2.putText(
        out,
        text,
        (12, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )

    dst = Path(output_image)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), out)
    return str(dst)
