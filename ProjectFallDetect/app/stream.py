import threading
import time
import cv2
import numpy as np
from datetime import datetime
import requests
import tensorflow as tf
from collections import deque
from PIL import Image
import io

model = tf.keras.models.load_model(r"./app\best_model_val_acc_3_29.keras")
labels = ["Fall Down", "Non-movement", "Sit Down", "Standing"]

def send_message_to_Discord(Discord_URL, message):
    data = {
        'content': message
    }
    response = requests.post(Discord_URL, json=data)
    print(response.status_code)
    return response.status_code

def send_image_to_Discord(frame, Discord_URL, message):

    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)
    payload = {
        "content": message 
    }
   
    byte_arr = io.BytesIO()
    pil_image.save(byte_arr, format='PNG')
    byte_arr.seek(0)

    files = {
        'file': ('image.png', byte_arr, 'image/png')
    }
    response = requests.post(Discord_URL,data=payload,files=files)

    return response.status_code

def preprocess_frame(frame, target_size=(224, 224)):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  
    frame = cv2.resize(frame, target_size) 
    frame = frame.astype('float32') / 255.0  
    frame = np.expand_dims(frame, axis=-1) 
    return frame

def start_rtsp_stream(rtsp_url, camera_name, discord_token, camera_message, room_name, is_notification, camera_threads, stop_flag=None,target_frames=30):
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    sent_initial_notification = False

    if not cap.isOpened():
        print(f"Error: Cannot open camera {camera_name} with RTSP URL: {rtsp_url}.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Camera {camera_name} (RTSP: {rtsp_url}) fps: {fps}")
    
    frame_list = deque(maxlen=target_frames)

    while True:
        if stop_flag and stop_flag.is_set():
            send_message_to_Discord(discord_token, f"✋ กล้อง {camera_name} หยุดการทำงานโดยผู้ใช้.")
            print(f"Camera {camera_name} stopped.")
            break

        ret, frameorg = cap.read()
        if not ret:
            send_message_to_Discord(discord_token, f"❌ ข้อผิดพลาด: กล้อง {camera_name} ไม่สามารถส่งเฟรมได้ กรุณาตรวจสอบการเชื่อมต่อกล้อง.")
            break 

        if not sent_initial_notification:
            success_message = f"✅ กล้อง {camera_name} (ห้อง {room_name}) เชื่อมต่อสำเร็จ"
            send_message_to_Discord(discord_token, success_message)
            sent_initial_notification = True

        frame = preprocess_frame(frameorg)
        frame_list.append(frame)

        if len(frame_list) == target_frames:
            input_data = np.array(frame_list)  
            input_data = np.expand_dims(input_data, axis=0) 

            predictions = model.predict(input_data)
            predicted_prob = predictions[0]
            predicted_label_idx = np.argmax(predicted_prob)
            predicted_label = labels[predicted_label_idx]

            if predicted_label == "Fall Down":
                print(f"\033[31mPrediction (Camera {camera_name}): Fall - {predicted_prob[predicted_label_idx]:.6f}\033[0m")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                full_message = f"""
                *📅 เวลา*: {timestamp}
                *📷 กล้อง*: {camera_name}
                *🏠 ห้อง*: {room_name}
                {camera_message}
                """

                if is_notification:
                    frame_noti = cv2.resize(frameorg, (360, 240))
                    send_image_to_Discord(frame_noti, discord_token, full_message)
                else:
                    send_message_to_Discord(discord_token, full_message)

            else:
                print(f"\033[32mPrediction (Camera {camera_name}): {predicted_label} - {predicted_prob[predicted_label_idx]:.6f}\033[0m")
            
            frame_list = deque(list(frame_list)[-(target_frames - int(fps)):], maxlen=target_frames)
            time.sleep(1 / int(fps)) 

    cap.release() 
    cv2.destroyAllWindows()
