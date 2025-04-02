import threading
import time
import cv2
import numpy as np
from datetime import datetime
import requests
import tensorflow as tf

model = tf.keras.models.load_model(r"./app\best_model_val_acc_3_29.keras")

labels = ["Fall Down", "Lying Down", "Sit Down", "Standing"]

def send_message_to_line(line_token, message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {line_token}"}
    payload = {'message': message}
    response = requests.post(url, headers=headers, data=payload)
    return response.status_code

def send_image_to_line(frame, line_token, message):
    _, img_encoded = cv2.imencode('.jpg', frame)
    img_bytes = img_encoded.tobytes()

    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {line_token}"}
    payload = {'message': message}
    files = {'imageFile': ('image.jpg', img_bytes, 'image/jpeg')}
    response = requests.post(url, headers=headers, data=payload, files=files)
    return response.status_code

def preprocess_frame(frame, target_size=(224, 224)):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame = cv2.resize(frame, target_size)  
    frame = frame.astype('float32') / 255.0  
    frame = np.expand_dims(frame, axis=-1)  
    return frame

from collections import deque
def start_rtsp_stream(rtsp_url, camera_name, line_token, camera_message, room_name, is_notification, camera_flags, camera_threads):
    camera_flags[camera_name] = False
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Video {camera_name} fps: {fps}")

    frame_list = deque(maxlen=30)
    frame_count = 0

    sent_initial_notification = False

    while True:
        if camera_flags[camera_name]:
            break

        ret, frame = cap.read()
        if not ret:
            # send_message_to_line(line_token, f"❌ ข้อผิดพลาด: กล้อง {camera_name} ไม่สามารถส่งเฟรมได้ กรุณาตรวจสอบการเชื่อมต่อกล้อง.")
            break

        if not sent_initial_notification:
            success_message = f"✅ กล้อง {camera_name} (ห้อง {room_name}) เชื่อมต่อสำเร็จ"
            # send_message_to_line(line_token, success_message)
            sent_initial_notification = True
    
        frame = preprocess_frame(frame)
        frame_list.append(frame)
        frame_count += 1

        if len(frame_list) == 30:
            input_data = np.array(frame_list)
            input_data = np.expand_dims(input_data, axis=0)

            predictions = model.predict(input_data)
            predicted_prob = predictions[0]
            predicted_label_idx = np.argmax(predicted_prob)
            predicted_label = labels[predicted_label_idx]

            if predicted_label == "Fall Down" and predicted_prob[predicted_label_idx] > 0.8:
                print(f"\033[31mPrediction (Video {camera_name}): Fall - {predicted_prob[predicted_label_idx]:.6f}\033[0m")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                full_message = f"""
                *📅 เวลา*: {timestamp}
                *📷 กล้อง*: {camera_name}
                *🏠 ห้อง*: {room_name}
                {camera_message}
                """

                # if is_notification:
                #     frame_noti = cv2.resize(frame, (360, 240))
                #     send_image_to_line(frame_noti, line_token, full_message)
                # else:
                #     send_message_to_line(line_token, full_message)
            
            elif predicted_label == "Sit Down":
                print(f"\033[32mPrediction (Video {camera_name}): Moving - {predicted_prob[predicted_label_idx]:.6f}\033[0m")
            elif predicted_label == "Standing":
                print(f"\033[32mPrediction (Video {camera_name}): Moving - {predicted_prob[predicted_label_idx]:.6f}\033[0m")
            elif predicted_label == "Lying Down":
                print(f"\033[32mPrediction (Video {camera_name}): Non movement - {predicted_prob[predicted_label_idx]:.6f}\033[0m")

            frame_list = deque(list(frame_list)[-(30 - int(fps)):], maxlen=30)

        time.sleep(1 / int(fps))
    
    cap.release()