def adaptive_fusion(face_score: float, cloth_score: float, face_quality: float) -> float:
    """
    Dynamic score fusion.

    High quality face -> trust face more.
    Low quality face -> trust clothing more.
    """
    if face_quality > 0.7:
        w_face, w_cloth = 0.8, 0.2
    elif face_quality > 0.4:
        w_face, w_cloth = 0.6, 0.4
    else:
        w_face, w_cloth = 0.3, 0.7

    return (w_face * float(face_score)) + (w_cloth * float(cloth_score))
