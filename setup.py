import os
import json

if not os.path.exists("music"):
    os.mkdir("music")

if not os.path.exists("data/config.json"):
    with open("data/config.json", "w") as f:
        json.dump({"volume": 100}, f)
        
os.system('python -m spotdl --download-ffmpeg')