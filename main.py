import threading
import tkinter as tk
import random
from pydub import AudioSegment
import pygame
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import tempfile
import os
import subprocess

class Song:
    def __init__(self, filepath):
        self.filepath = filepath
        try:
            audio = MP3(filepath, ID3=EasyID3)
            self.title = audio['title'][0] if 'TIT2' in audio else os.path.splitext(os.path.basename(filepath).split(" - ", 1)[1])[0]
            self.album = audio.get('TALB')  # Get album name, if not found return empty string
        except (KeyError, ValueError):  # Handle cases where MP3 or ID3 data is missing/corrupted
            self.title = os.path.splitext(os.path.basename(filepath).split(" - ", 1)[1])[0]
            self.album = ''

class SongFragment:
    def __init__(self, song):
        self.song = song
        self.fragment_data = self.create_fragment()

    def create_fragment(self):
        try:
            song_duration = AudioSegment.from_file(self.song.filepath).duration_seconds
            start_time = random.randint(10, int(song_duration - 20))
            end_time = start_time + 10
            cmd = f'ffmpeg -i "{self.song.filepath}" -ss {start_time} -to {end_time} -c:a libmp3lame temp.mp3'
            subprocess.call(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            with open("temp.mp3", "rb") as f:
                return f.read()
        except Exception as e:
            print(f"Error processing {self.song.filepath}, skipping... Error: {str(e)}")
            return None

class SongLibrary:
    def __init__(self, songs_dir):
        self.songs_dir = songs_dir

    def get_songs(self):
        songs = []
        for root, _, files in os.walk(self.songs_dir):
            for file in files:
                if file.endswith(".mp3"):
                    try:
                        MP3(os.path.join(root, file))  # Check if valid MP3
                        songs.append(Song(os.path.join(root, file)))
                    except:
                        print(f"Error reading {file}, skipping...")
        return songs

class SongGuesser:
    def __init__(self, master):
        self.master = master
        master.title("Song Guesser")

        self.songs_dir = "music"
        if not os.path.exists(self.songs_dir):
            os.mkdir(self.songs_dir)

        self.song_library = SongLibrary(self.songs_dir)

        self.score = tk.StringVar()
        self.score.set("0")
        self.score_label = tk.Label(master, textvariable=self.score)
        self.score_label.grid(row=0, column=0, columnspan=2)

        self.choices_lock = threading.Lock()
        self.correct_song = None
        self.choices = []
        self.options = [
            tk.Button(master, text="", command=lambda i=i: self.check_answer(i), width=50, height=2, state=tk.DISABLED)
            for i in range(4)
        ]
        for option in self.options:
            option.grid(row=self.options.index(option) + 1, column=0, columnspan=2)

        self.play_button = tk.Button(master, text="Play song", command=self.play_song, width=29, height=2)
        self.play_button.grid(row=5, column=0)

        self.pause_button = tk.Button(master, text="Pause", command=self.pause_song, state=tk.DISABLED, width=19, height=2)
        self.pause_button.grid(row=5, column=1)

        pygame.mixer.init()

    def get_random_choices(self, songs, correct_song):
        choices = [correct_song]
        while len(choices) < 4:
            random_song = random.choice(songs)
            if random_song not in choices:
                choices.append(random_song)
        random.shuffle(choices)
        return choices

    def check_answer(self, choice_index):
        with self.choices_lock:
            if self.choices[choice_index] == self.correct_song:
                self.score.set(str(int(self.score.get()) + 1))
                root.update_idletasks()
            else:
                print(f"Wrong! The correct answer was {self.correct_song.title}")
        self.play_song()

    def update_options(self):
        new_choices = self.get_random_choices(self.song_library.get_songs(), self.correct_song)
        with self.choices_lock:
            self.choices = new_choices
        for i, choice in enumerate(self.choices): 
            # Update button text to include album name if available
            self.options[i]['text'] = f"{choice.title}   ({choice.album})" if choice.album else choice.title
                    
    def play_song(self):
        if os.path.exists("temp.mp3"):
            os.remove("temp.mp3")
        songs = self.song_library.get_songs() 
        if not songs:
            print("No valid MP3 files found in the 'music' directory.")
            return
    
        self.correct_song = random.choice(songs)
    
        # Start updating options before generating and playing song fragment
        threading.Thread(target=self.update_options).start()
    
        song_fragment = SongFragment(self.correct_song) 
        fragment = song_fragment.fragment_data 
    
        if fragment:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_filename = f.name
                f.write(fragment)
    
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
    
            self.play_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            for option in self.options:
                option.config(state=tk.NORMAL)
        else:
            print(f"Error playing {self.correct_song.filepath}. Skipping...")

    def pause_song(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.pause_button.config(text="Resume")
        else:
            pygame.mixer.music.unpause()
            self.pause_button.config(text="Pause")

root = tk.Tk()
guesser = SongGuesser(root)
root.mainloop()
pygame.mixer.quit()

