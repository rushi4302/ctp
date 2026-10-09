def combine(image_result, text_result):

    # Highest priority: NLP
    if text_result:

        return {
            "category": text_result["category"],
            "confidence": text_result["confidence"],
            "source": "NLP Model"
        }


    # Only image available
    elif image_result:

        return {
            "category": image_result["category"],
            "confidence": image_result["confidence"],
            "source": "Image Model"
        }


    else:

        return {
            "category": "No input provided",
            "confidence": 0,
            "source": "None"
        }