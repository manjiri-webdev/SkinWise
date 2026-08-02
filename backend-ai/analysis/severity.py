def calculate_severity(summary):
    total = summary["total_lesions"]

    if total <= 10:
        return {
            "level": "Mild",
            "score": total
        }

    elif total <= 30:
        return {
            "level": "Moderate",
            "score": total
        }

    else:
        return {
            "level": "Severe",
            "score": total
        }