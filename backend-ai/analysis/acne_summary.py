from collections import Counter

def summarize_acne(detections):
    counter = Counter()

    for d in detections:
        counter[d["class_name"]] += 1

    return {
        "blackheads": counter.get("blackheads", 0),
        "whiteheads": counter.get("whiteheads", 0),
        "papules": counter.get("papules", 0),
        "pustules": counter.get("pustules", 0),
        "nodules": counter.get("nodules", 0),
        "dark_spots": counter.get("dark spot", 0) + counter.get("dark_spots", 0) + counter.get("dark spots", 0),
        "total_lesions": len(detections)
    }