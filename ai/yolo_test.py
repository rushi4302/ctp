from ultralytics import YOLO

# Load YOLO model
model = YOLO("yolov8n.pt")

# Test image
results = model("test_images/sample.jpg")

# Print detections
for result in results:
    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        print(
            "Class:",
            model.names[class_id],
            "Confidence:",
            confidence
        )