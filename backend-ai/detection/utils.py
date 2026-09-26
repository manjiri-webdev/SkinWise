def calculate_iou(bbox1, bbox2):
    """
    Calculate Intersection over Union (IoU) for two bounding boxes.
    """
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2
    
    # Calculate intersection
    x_left = max(x1_1, x1_2)
    y_top = max(y1_1, y1_2)
    x_right = min(x2_1, x2_2)
    y_bottom = min(y2_1, y2_2)
    
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    # Calculate union
    bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    bbox2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = bbox1_area + bbox2_area - intersection_area
    
    if union_area == 0:
        return 0.0
    
    return intersection_area / union_area


def apply_nms(detections, iou_threshold=0.5):
    """
    Apply Non-Maximum Suppression to remove overlapping detections of the same class.
    Keeps the highest confidence detection when boxes overlap above threshold.
    """
    if not detections:
        return []
    
    # Group detections by class
    class_groups = {}
    for det in detections:
        class_name = det["class_name"]
        if class_name not in class_groups:
            class_groups[class_name] = []
        class_groups[class_name].append(det)
    
    # Apply NMS per class
    cleaned_detections = []
    
    for class_name, class_detections in class_groups.items():
        # Sort by confidence (highest first)
        class_detections.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Apply NMS
        selected = []
        while class_detections:
            # Select the highest confidence detection
            current = class_detections.pop(0)
            selected.append(current)
            
            # Remove detections that overlap significantly with current
            remaining = []
            for det in class_detections:
                iou = calculate_iou(current["bbox"], det["bbox"])
                if iou < iou_threshold:
                    remaining.append(det)
            
            class_detections = remaining
        
        cleaned_detections.extend(selected)
    
    return cleaned_detections


def parse_yolo_results(results):
    """
    Convert YOLO results into structured JSON and apply NMS to remove duplicates.
    """

    parsed = []

    result = results[0]

    print(f"DEBUG: Raw YOLO boxes count: {len(result.boxes)}")

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

    print(f"DEBUG: Parsed detections count: {len(parsed)}")

    # Apply NMS to remove overlapping detections of the same class
    cleaned = apply_nms(parsed, iou_threshold=0.5)  # Standard IoU threshold
    
    print(f"NMS: Before count: {len(parsed)}, After count: {len(cleaned)}")
    
    return cleaned