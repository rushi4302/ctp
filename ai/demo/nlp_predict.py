from transformers import pipeline


classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)


categories = [
    "pothole",
    "garbage",
    "water leakage",
    "street light issue",
    "road damage",
    "traffic problem"
]


def predict_text(text):

    result = classifier(
        text,
        categories
    )


    category = result["labels"][0]

    confidence = result["scores"][0] * 100


    return {

        "category": category,

        "confidence": round(
            confidence,
            2
        )

    }