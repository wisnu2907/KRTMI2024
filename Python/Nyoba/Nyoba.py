import os
import time

import cv2
import numpy as np
import serial.tools.list_ports
import torch
import serial
from ultralytics import YOLO    

Motor1 = serial.Serial("COM8", 9600) #ID 10
Motor2 = serial.Serial("COM7", 9600) #ID 11

if Motor1.is_open:
    Motor1.close()

# Open the serial port
Motor1.open()
# print("Connected Motor1")

if Motor2.is_open:
    Motor2.close()

# Open the serial port
Motor2.open()
# print("Connected Motor2")


# Initialize the YOLO model
model = YOLO("Python\\CV\\best.pt")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.model.to(device)

# setting device on GPU if available, else CPU)
print("Using device:", device)


cap = cv2.VideoCapture(0)  


# Define the colors for the bounding boxes
COLORS = [(0, 255, 0)]

# Load calibration settings if the file exists
calibration_file = "calibration_settings.npz"
if os.path.exists(calibration_file):
    settings = np.load(calibration_file)
    pts1 = settings["pts1"]
    pts2 = settings["pts2"]
    calibrated = True
    print("Calibration settings loaded.")
    
else:
    calibrated = False
    
time.sleep(2)
Motor1.write("3".encode('utf-8'))
Motor2.write("3".encode('utf-8'))
time.sleep(8.5)
Motor1.write("0".encode('utf-8'))
Motor2.write("0".encode('utf-8'))
    
counter = 0
detected_classes = []


while True:
    # Read a frame from the webcam
    ret, frame = cap.read()
    # Calibration
    if calibrated:
        # Resize the frame based on the calibration points
        width = int(np.sqrt((pts1[1][0] - pts1[0][0]) ** 2 + (pts1[1][1] - pts1[0][1]) ** 2))
        height = int(np.sqrt((pts1[2][0] - pts1[1][0]) ** 2 + (pts1[2][1] - pts1[1][1]) ** 2))
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        frame = cv2.warpPerspective(frame, matrix, (width, height))


    # Perform object detection on the frame
    results = model.predict(source=frame, show=False, conf=0.5)
    results[0].boxes = results[0].boxes.to(device)

    # ratio pixel to cm
    ratio_px_cm = 194 / 100
    
    if len(results[0].boxes) == 0:
        Motor1.write("1".encode('utf-8'))
        Motor2.write("1".encode('utf-8'))
        
    # Draw the detection results on the frame
    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0]
        conf = box.conf[0]
        cls = box.cls[0]
        class_name = model.names[int(cls)]
        label = f"{model.names[int(cls)]}: {conf:.2f}"
        color = COLORS[int(cls) % len(COLORS)]

        # Draw bounding box
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

        # Calculate and display the center coordinates in centimeters
        center_x_cm = ((int((x1 + x2) / 2) - frame.shape[1] // 2) / ratio_px_cm / 10)  

        center_y_cm = (y1 / ratio_px_cm / 10)  
        
        center_x = int((x1 + x2) / 2) - frame.shape[1] // 2
        center_y = frame.shape[0] // 2 - int((y1 + y2) / 2)
        cv2.circle(frame, (int(center_x_cm), int(center_y_cm)), 5, (0, 255, 255), -1)

        # Draw labelq
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.putText(frame, label, (int(x1), int(y2) + label_size[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2,)
        cv2.putText(frame, label, (int(x1), int(y1) - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2,)

        # Draw center coordinates in centimeters
        cv2.putText(frame, f"Center (cm): ({center_x_cm:.3f} cm, {center_y_cm:.3f} cm)", (int(x1), int(y2) + label_size[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2,)
        cv2.putText(frame, f"Center (cm): ({center_x_cm:.3f} cm, {center_y_cm:.3f} cm)", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2,)
        
        if center_x_cm > 4.0:
            Motor1.write("1".encode('utf-8'))
            Motor2.write("1".encode('utf-8'))
        elif center_x_cm < 3.0 and center_x_cm > -3.0:
            if class_name not in detected_classes:
                detected_classes.append(class_name)
                Motor1.write("1".encode('utf-8'))
                Motor2.write("1".encode('utf-8'))
                cv2.putText(frame, f"PROSES AMBIL SAMPAH KE {counter}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
                counter += 1
                time.sleep(2)
            else:
                Motor1.write("0".encode('utf-8'))
                Motor2.write("0".encode('utf-8'))
                time.sleep(3)              
        elif center_x_cm < -3.0:
            Motor1.write("2".encode('utf-8'))
            Motor2.write("2".encode('utf-8'))

    # Display the frame with counter
    cv2.putText(frame, f"Counter: {counter}", (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2,)
    
    # Display the frame
    cv2.imshow("Astro_24", frame)

    # Exit if the user presses the 'q' key
    if cv2.waitKey(1) & 0xFF == ord("q"):
        Motor1.write("0".encode('utf-8'))
        Motor2.write("0".encode('utf-8'))
        break
    
# Release the webcam and destroy all windows
cap.release()
Motor1.close()
Motor2.close()
cv2.destroyAllWindows()
exit()