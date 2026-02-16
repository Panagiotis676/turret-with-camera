from ultralytics import YOLO

# Load small YOLO model
model = YOLO("yolov8n.pt")

# Use laptop webcam (source=0)
model(source=0, show=True)
