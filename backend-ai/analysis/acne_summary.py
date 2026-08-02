from collections import Counter

def summarize_acne(detections):
    counter = Counter()

    for d in detections:
        counter[d["class_name"]] += 1

    return {
        "blackheads": counter["blackheads"],
        "whiteheads": counter["whiteheads"],
        "papules": counter["papules"],
        "pustules": counter["pustules"],
        "nodules": counter["nodules"],
        "dark_spots": counter["dark spot"],
        "total_lesions": len(detections)
    }