import threading
import tkinter as tk
import random
from pydub import AudioSegment
import pygame
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import tempfile
import os

if not os.path.exists("songs"):
    os.mkdir("songs")
    
def get_songs():
    songs = []
    for root, _, files in os.walk("songs"):
        for file in files:
            if file.endswith(".mp3"):
                try:
                    MP3(os.path.join(root, file))  # Check if valid MP3
                    songs.append(os.path.join(root, file))
                except:
                    print(f"Error reading {file}, skipping...")
    return songs

def get_song_fragment(song):
    try:
        song_duration = AudioSegment.from_file(song).duration_seconds * 1000
        start_time = random.randint(10000, int(song_duration - 20000))
        end_time = start_time + 10000
        fragment = AudioSegment.from_file(song)[start_time:end_time]
        with fragment.export(format="mp3") as f:
            return f.read()
    except:
        print(f"Error processing {song}, skipping...")
        return None 

def get_random_choices(songs, correct_song):
    choices = [correct_song]
    while len(choices) < 4:
        random_song = random.choice(songs)
        if random_song not in choices:
            choices.append(random_song)
    random.shuffle(choices)
    return choices

def main():
    choices_lock = threading.Lock()
    
    def check_answer(choice_index):
        nonlocal score
        with choices_lock:
            if choices[choice_index] == correct_song:
                score.set(str(int(score.get()) + 1))
            else:
                print(f"Wrong! The correct answer was {correct_song[6:]}")
        play_song()  # Start a new round
        
    def play_song():
        nonlocal correct_song, choices
        songs = get_songs()
        if not songs:
            print("No valid MP3 files found in the 'songs' directory.")
            return

        correct_song = random.choice(songs)
        fragment = get_song_fragment(correct_song)

        if fragment:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_filename = f.name  # Get the temporary filename
                f.write(fragment)

            pygame.mixer.init()
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()

            def update_options():
                nonlocal choices
                new_choices = get_random_choices(songs, correct_song)
                with choices_lock:
                    choices = new_choices
                for i, _ in enumerate(options):
                    audio = MP3(choices[i], ID3=EasyID3)
                    if 'TIT2' in audio:
                        options[i]['text'] = audio['title'][0]
                    else:
                        filename = os.path.basename(choices[i])
                        title = filename.split(" - ", 1)[1]
                        title = os.path.splitext(title)[0]
                        options[i]['text'] = title

            threading.Thread(target=update_options).start()

            play_button.config(state=tk.DISABLED)
            pause_button.config(state=tk.NORMAL)
        else:
            print(f"Error playing {correct_song}. Skipping...")

    def pause_song():
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            pause_button.config(text="Resume")
        else:
            pygame.mixer.music.unpause()
            pause_button.config(text="Pause")
            
    root = tk.Tk()
    root.title("Song Guesser")

    score = tk.StringVar()
    score.set("0")
    score_label = tk.Label(root, textvariable=score)
    score_label.pack()

    correct_song = None
    choices = []

    # Create buttons for song options
    options = [tk.Button(root, text="", command=lambda i=i: check_answer(i), width=50, height=2) 
               for i in range(4)]
    for option in options:
        option.pack()

    play_button = tk.Button(root, text="Play song", command=play_song)
    play_button.pack()

    pause_button = tk.Button(root, text="Pause", command=pause_song, state=tk.DISABLED)
    pause_button.pack()

    root.mainloop()
    pygame.mixer.quit()

if __name__ == "__main__":
    main()