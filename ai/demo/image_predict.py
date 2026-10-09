import numpy as np
from PIL import Image
import tensorflow as tf


# Load TFLite model
interpreter = tf.lite.Interpreter(
    model_path="model/civic_model.tflite"
)

interpreter.allocate_tensors()


# Get input/output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()


# Load labels
with open("model/labels.txt", "r") as f:
    labels = [
        line.strip()
        for line in f.readlines()
    ]


def predict_image(image):

    # Convert image
    img = image.resize((224, 224))

    img = np.array(img)


    # Handle grayscale images
    if len(img.shape) == 2:
        img = np.stack((img,) * 3, axis=-1)


    # Normalize
    img = img.astype(np.float32) / 255.0


    # Add batch dimension
    img = np.expand_dims(
        img,
        axis=0
    )


    # Prediction
    interpreter.set_tensor(
        input_details[0]["index"],
        img
    )


    interpreter.invoke()


    output = interpreter.get_tensor(
        output_details[0]["index"]
    )


    prediction_index = np.argmax(output)


    confidence = float(
        np.max(output) * 100
    )


    category = labels[prediction_index]


    return {

        "category": category,

        "confidence": round(
            confidence,
            2
        )
    }