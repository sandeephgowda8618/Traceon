import cv2


def draw_bbox(image, bbox, score: float):
    """Draw person bbox with adaptive fusion score label."""
    x1, y1, x2, y2 = map(int, bbox)
    annotated = image.copy()

    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 220, 0), 2)
    label = f"match={score:.3f}"
    cv2.putText(
        annotated,
        label,
        (x1, max(20, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 220, 0),
        2,
    )
    return annotated
