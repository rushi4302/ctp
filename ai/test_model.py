import tensorflow as tf
import numpy as np
from PIL import Image


# Load model
model_path = "model/civic_model.tflite"

interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()


input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Model loaded successfully")

# Load labels
with open("model/labels.txt", "r") as f:
    labels = [line.strip() for line in f.readlines()]


# Test image
image_path = "test_images/sample2.jpg"

img = Image.open(image_path)

# Resize according to model input
input_shape = input_details[0]["shape"]
height = input_shape[1]
width = input_shape[2]

img = img.resize((width, height))

# Convert image to numpy
img_array = np.array(img)

# Normalize (MobileNet expects 0-1)
img_array = img_array.astype(np.float32) / 255.0

# Add batch dimension
img_array = np.expand_dims(img_array, axis=0)


# Run inference
interpreter.set_tensor(
    input_details[0]["index"],
    img_array
)

interpreter.invoke()


# Get prediction
output = interpreter.get_tensor(
    output_details[0]["index"]
)

prediction = np.argmax(output[0])
confidence = output[0][prediction]


print("Prediction:", labels[prediction])
print("Confidence:", confidence)