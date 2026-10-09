import json
import re


# Load categories
with open("nlp/categories.json", "r") as file:
    categories = json.load(file)


def preprocess(text):
    """
    Convert text into clean format
    """
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text


def classify_issue(description):

    description = preprocess(description)

    scores = {}

    for category, keywords in categories.items():

        score = 0

        for keyword in keywords:
            if keyword in description:
                score += 1

        scores[category] = score


    # Find best category
    best_category = max(scores, key=scores.get)

    total_matches = scores[best_category]


    if total_matches == 0:
        return {
            "category": "Other",
            "confidence": 0
        }


    confidence = min(total_matches / 3, 1)


    return {
        "category": best_category,
        "confidence": round(confidence, 2)
    }



# Testing
if __name__ == "__main__":

    text = input("Enter complaint: ")

    result = classify_issue(text)

    print(result)