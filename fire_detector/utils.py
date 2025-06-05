import os
import cv2
import torch
import numpy as np
from django.conf import settings
from ultralytics import YOLO
import tempfile
from pathlib import Path

def load_model():
    """Load the YOLO model"""
    model_path = settings.YOLO_MODEL_PATH
    model = YOLO(model_path)
    return model

def detect_fire_in_image(image_path, output_dir):
    """Detect fire in an image using YOLO model"""
    model = load_model()
    
    # Run inference
    results = model.predict(source=image_path, conf=0.5, save=True, project=output_dir)
    
    # Check if fire is detected (class 0 is fire)
    has_fire = False
    confidence = 0.0
    
    if len(results) > 0:
        result = results[0]
        if hasattr(result, 'boxes') and len(result.boxes) > 0:
            for box in result.boxes:
                cls = int(box.cls[0].item())
                conf = box.conf[0].item()
                if cls == 0:  # Assuming class 0 is fire
                    has_fire = True
                    if conf > confidence:
                        confidence = conf
    
    # Get the path to the saved result image
    result_path = None
    for file in os.listdir(output_dir):
        if file.startswith('predict') and os.path.isdir(os.path.join(output_dir, file)):
            predict_dir = os.path.join(output_dir, file)
            for img_file in os.listdir(predict_dir):
                if img_file.endswith(('.jpg', '.jpeg', '.png')):
                    result_path = os.path.join(predict_dir, img_file)
                    break
            if result_path:
                break
    
    return has_fire, confidence, result_path

def detect_fire_in_video(video_path, output_dir):
    """Detect fire in a video using YOLO model and convert to MP4"""
    model = load_model()
    
    # Open the input video
    cap = cv2.VideoCapture(video_path)
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Create output video path with .mp4 extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_video_path = os.path.join(output_dir, f"{video_name}_processed.mp4")
    
    # Use MP4V codec for better web compatibility
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    # Initialize detection variables
    has_fire = False
    max_confidence = 0.0
    fire_frame_count = 0
    
    print(f"Processing video: {total_frames} frames")
    
    frame_number = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_number += 1
        print(f"Processing frame {frame_number}/{total_frames}")
        
        # Run YOLO detection on the frame
        results = model.predict(source=frame, conf=0.5, save=False, verbose=False)
        
        # Process detection results
        frame_has_fire = False
        frame_confidence = 0.0
        
        if len(results) > 0:
            result = results[0]
            if hasattr(result, 'boxes') and len(result.boxes) > 0:
                for box in result.boxes:
                    cls = int(box.cls[0].item())
                    conf = box.conf[0].item()
                    
                    if cls == 0:  # Fire class
                        frame_has_fire = True
                        frame_confidence = max(frame_confidence, conf)
                        
                        # Draw bounding box
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, f'Fire {conf:.2f}', (x1, y1-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Update overall detection status
        if frame_has_fire:
            has_fire = True
            fire_frame_count += 1
            max_confidence = max(max_confidence, frame_confidence)
        
        # Add detection text to frame
        detection_text = "Fire Detected" if frame_has_fire else "No Fire Detected"
        text_color = (0, 0, 255) if frame_has_fire else (0, 255, 0)
        cv2.putText(frame, detection_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)
        
        # Add confidence score if fire is detected
        if frame_has_fire:
            cv2.putText(frame, f'Confidence: {frame_confidence:.2f}', (50, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2, cv2.LINE_AA)
        
        # Write frame to output video
        out.write(frame)
    
    # Release resources
    cap.release()
    out.release()
    
    print(f"Video processing complete. Fire detected in {fire_frame_count}/{total_frames} frames")
    
    # Convert to web-compatible MP4 if needed
    web_compatible_path = convert_to_web_mp4(output_video_path)
    
    return has_fire, max_confidence, web_compatible_path

def convert_to_web_mp4(input_path):
    """Convert video to web-compatible MP4 format using ffmpeg if available, otherwise return original"""
    try:
        import subprocess
        
        # Create output path with _web suffix
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_web.mp4"
        
        # Try to use ffmpeg for better web compatibility
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264',  # H.264 codec
            '-c:a', 'aac',      # AAC audio codec
            '-movflags', '+faststart',  # Enable fast start for web
            '-y',  # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Successfully converted to web-compatible MP4")
            # Remove the original file to save space
            os.remove(input_path)
            return output_path
        else:
            print(f"FFmpeg conversion failed: {result.stderr}")
            return input_path
            
    except (ImportError, FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"FFmpeg not available or failed: {e}")
        print("Using OpenCV output (may have compatibility issues)")
        return input_path

def process_upload(detection):
    """Process uploaded file and run fire detection"""
    file_path = detection.uploaded_file.path
    output_dir = os.path.join(settings.MEDIA_ROOT, 'results', str(detection.id))
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        if detection.is_video:
            has_fire, confidence, result_path = detect_fire_in_video(file_path, output_dir)
        else:
            has_fire, confidence, result_path = detect_fire_in_image(file_path, output_dir)
        
        # Update detection object
        detection.has_fire = has_fire
        detection.confidence = confidence
        
        # Save result file path if available
        if result_path and os.path.exists(result_path):
            # Get relative path for database storage
            rel_path = os.path.relpath(result_path, settings.MEDIA_ROOT)
            detection.result_file = rel_path
        
        detection.save()
        print(f"Detection complete: Fire={has_fire}, Confidence={confidence:.2f}")
        
    except Exception as e:
        print(f"Error processing upload: {e}")
        # Set some default values in case of error
        detection.has_fire = False
        detection.confidence = 0.0
        detection.save()
    
    return detection