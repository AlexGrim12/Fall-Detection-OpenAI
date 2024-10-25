import cv2
import numpy as np
from ultralytics import YOLO
import cvzone
import requests
import time
from datetime import datetime
from collections import deque  # Usamos deque para el buffer de frames


def RGB(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE:
        point = [x, y]
        print(point)


def send_fall_alert(track_id, confidence, location, images):
    try:
        url = "http://localhost:5000/fall_alert"
        # Datos del formulario
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "track_id": track_id,
            "confidence": confidence,
            "location": location,
            "camera_id": "webcam_1",
        }

        # Archivos de imágenes a enviar
        files = [("images", open(image, "rb")) for image in images]

        # Envío de la solicitud POST con los datos y las imágenes
        response = requests.post(url, data=data, files=files)

        if response.status_code == 200:
            print("Alerta y imágenes enviadas correctamente.")
        else:
            print(f"Error al enviar la alerta: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error al enviar alerta: {e}")


# Configuración inicial
cv2.namedWindow("RGB")
cv2.setMouseCallback("RGB", RGB)

# Cargar modelo YOLO
model = YOLO("yolo11n.pt")
names = model.model.names

# Inicializar webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: No se pudo abrir la webcam")
    exit()

# Configurar propiedades de la cámara
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

count = 0
last_alert_time = {}  # Diccionario para tracking de últimas alertas por ID

frame_buffer = deque(maxlen=10)  # Almacenamos los últimos 10 frames antes de la caída

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error al leer frame de la webcam")
        break

    count += 1
    if count % 3 != 0:
        continue

    frame = cv2.resize(frame, (1020, 600))

    # Guardar el frame actual en el buffer
    frame_buffer.append(frame.copy())

    # Ejecutar tracking de YOLOv8
    results = model.track(frame, persist=True, classes=0)

    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        confidences = results[0].boxes.conf.cpu().tolist()

        for box, class_id, track_id, conf in zip(
            boxes, class_ids, track_ids, confidences
        ):
            c = names[class_id]
            x1, y1, x2, y2 = box
            h = y2 - y1
            w = x2 - x1
            thresh = h - w

            current_time = time.time()

            if thresh <= 0:  # Detección de caída
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cvzone.putTextRect(frame, f"{track_id}", (x1, y2), 1, 1)
                cvzone.putTextRect(frame, f"{'Fall'}", (x1, y1), 1, 1)

                # Guardar solo el frame 10 antes de la caída y el frame de la caída
                if len(frame_buffer) == 10:
                    frame_before_fall = frame_buffer[
                        0
                    ]  # El frame más antiguo del buffer (10 antes)
                else:
                    frame_before_fall = frame_buffer[
                        0
                    ]  # En caso de que no haya 10 frames previos, usar el primero disponible
                fall_frame = frame  # Frame actual de la caída

                # Guardar ambos frames en archivos
                before_fall_img_path = "frame_before_fall.png"
                fall_img_path = "fall_frame.png"
                cv2.imwrite(before_fall_img_path, frame_before_fall)
                cv2.imwrite(fall_img_path, fall_frame)

                # Enviar los dos frames como imágenes
                image_files = [before_fall_img_path, fall_img_path]

                # Enviar alerta y las imágenes solo si han pasado más de 30 segundos desde la última alerta para este ID
                if (
                    track_id not in last_alert_time
                    or (current_time - last_alert_time[track_id]) > 30
                ):
                    location = {"x": int((x1 + x2) / 2), "y": int((y1 + y2) / 2)}
                    if send_fall_alert(track_id, conf, location, image_files):
                        last_alert_time[track_id] = current_time
                        cvzone.putTextRect(frame, "Alert Sent!", (50, 50), 2, 2)

            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cvzone.putTextRect(frame, f"{track_id}", (x1, y2), 1, 1)
                cvzone.putTextRect(frame, f"{'Normal'}", (x1, y1), 1, 1)

    cv2.imshow("RGB", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
