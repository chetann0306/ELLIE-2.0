import cv2
from collections import Counter
import os

def capture_frame():
    """Silently grabs a single frame from your webcam."""
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    return ret, frame

def detect_objects():
    """Uses YOLOv8 to see what is in front of the camera."""
    from ultralytics import YOLO
    
    # Loads the 'nano' YOLOv8 model (super fast for local use)
    model = YOLO('yolov8n.pt') 
    
    ret, frame = capture_frame()
    if not ret:
        return "Sorry, I can't seem to access your camera right now."
        
    # Run the image through the AI
    results = model(frame, verbose=False)
    detected_items = []
    
    for r in results:
        for c in r.boxes.cls:
            detected_items.append(model.names[int(c)])
            
    if not detected_items:
        return "I'm looking, but I don't see anything I recognize clearly."
        
    # Count the items so she sounds natural (e.g., "2 chairs")
    item_counts = Counter(detected_items)
    description = []
    for item, count in item_counts.items():
        if count == 1:
            description.append(f"a {item}")
        else:
            description.append(f"{count} {item}s")
            
    # Format the sentence perfectly
    if len(description) == 1:
        final_string = description[0]
    else:
        final_string = ", ".join(description[:-1]) + " and " + description[-1]
        
    return f"Right now, I see {final_string} in front of me."

def recognize_face():
    """Detects faces in front of the camera."""
    import face_recognition
    
    ret, frame = capture_frame()
    if not ret:
        return "My camera is currently offline."

    # Convert OpenCV BGR image to RGB for face_recognition
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    
    if len(face_locations) == 0:
        return "I don't see anyone in front of the camera."
    
    # --- OPTIONAL: RECOGNIZE YOU SPECIFICALLY ---
    # To use this, put a clear picture of your face named 'me.jpg' in your backend folder!
    try:
        my_image_path = os.path.join(os.path.dirname(__file__), "me.jpg")
        if os.path.exists(my_image_path):
            my_image = face_recognition.load_image_file(my_image_path)
            my_face_encoding = face_recognition.face_encodings(my_image)[0]
            unknown_face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for unknown_encoding in unknown_face_encodings:
                results = face_recognition.compare_faces([my_face_encoding], unknown_encoding)
                if results[0]:
                    return "You are my creator, Chaitanya! Hello there."
    except Exception as e:
        print(f"Face match error: {e}")
    
    # Fallback if she doesn't recognize the specific face
    if len(face_locations) == 1:
        return "I see one person looking at me, but I don't know their name yet."
    else:
        return f"I see {len(face_locations)} people in front of me."
    