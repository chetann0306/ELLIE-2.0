import cv2
import numpy as np
from PIL import Image
import os
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).resolve().parent

print(f"Script directory: {script_dir}")

# Define paths - go UP one level if we're in backend/auth
if script_dir.name == 'auth':
    # If script is in backend/auth directory
    base_dir = script_dir.parent.parent
elif script_dir.name == 'ELLIE':
    # If script is in ELLIE directory (correct location)
    base_dir = script_dir
else:
    # Default to script directory
    base_dir = script_dir

print(f"Base directory: {base_dir}")

# Define paths relative to base
backend_dir = base_dir / 'backend' / 'auth'
samples_dir = backend_dir / 'samples'
trainer_dir = backend_dir / 'trainer'
cascade_file = backend_dir / 'haarcascade_frontalface_default.xml'

print(f"Samples directory: {samples_dir}")
print(f"Trainer directory: {trainer_dir}")
print(f"Cascade file: {cascade_file}")

# Check if paths exist
if not samples_dir.exists():
    print(f"ERROR: Samples directory not found at {samples_dir}")
    print("Please run sample.py first to capture face samples")
    exit(1)

if not cascade_file.exists():
    print(f"ERROR: Cascade file not found at {cascade_file}")
    exit(1)

# Create trainer directory if it doesn't exist
trainer_dir.mkdir(parents=True, exist_ok=True)

recognizer = cv2.face.LBPHFaceRecognizer_create()
detector = cv2.CascadeClassifier(str(cascade_file))


def Images_And_Labels(path):
    """
    Function to fetch the images and labels from the samples directory
    """
    path = Path(path)
    imagePaths = list(path.glob('*.jpg'))
    
    if not imagePaths:
        print(f"ERROR: No JPG files found in {path}")
        return [], []
    
    print(f"Found {len(imagePaths)} image files")
    
    faceSamples = []
    ids = []

    for imagePath in imagePaths:
        try:
            gray_img = Image.open(imagePath).convert('L')
            img_arr = np.array(gray_img, 'uint8')

            # Extract ID from filename (face.ID.count.jpg)
            parts = imagePath.stem.split(".")
            if len(parts) >= 2:
                id = int(parts[1])
            else:
                print(f"Warning: Could not extract ID from {imagePath.name}, skipping")
                continue
            
            faces = detector.detectMultiScale(img_arr)

            for (x, y, w, h) in faces:
                faceSamples.append(img_arr[y:y+h, x:x+w])
                ids.append(id)
                
        except Exception as e:
            print(f"Error processing {imagePath.name}: {e}")
            continue

    return faceSamples, ids


print("\nTraining faces. It will take a few seconds. Wait ...")

try:
    faces, ids = Images_And_Labels(samples_dir)
    
    if len(faces) == 0:
        print("ERROR: No faces found in training data!")
        print("Please run sample.py first to capture face samples")
        exit(1)
    
    print(f"Found {len(faces)} face samples from {len(set(ids))} unique user(s)")
    
    print("Training model...")
    recognizer.train(faces, np.array(ids))
    
    trainer_file = trainer_dir / 'trainer.yml'
    recognizer.write(str(trainer_file))
    
    print(f"\n✓ Model trained successfully!")
    print(f"✓ Trainer saved to: {trainer_file}")
    print("✓ You can now recognize faces using recognizer.py")
    
except Exception as e:
    print(f"Error during training: {e}")
    import traceback
    traceback.print_exc()
    exit(1)