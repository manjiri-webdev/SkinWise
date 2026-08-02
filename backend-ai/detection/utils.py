def parse_yolo_results(results):
    """
    Convert YOLO results into structured JSON.
    """

    parsed = []

    result = results[0]

    for box in result.boxes:

        cls_id = int(box.cls.item())
        confidence = float(box.conf.item())

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        parsed.append({
            "class_id": cls_id,
            "class_name": result.names[cls_id],
            "confidence": round(confidence, 3),
            "bbox": [
                round(x1, 2),
                round(y1, 2),
                round(x2, 2),
                round(y2, 2)
            ]
        })

    return parsed