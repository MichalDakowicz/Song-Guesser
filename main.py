import threading
import customtkinter as ctk
import random
from pydub import AudioSegment
import pygame
from mutagen.mp3 import MP3
import tempfile
import os
import subprocess
import json
from tkinter import messagebox, filedialog
from PIL import Image
import time

from downloader import main
if not os.path.exists("data/config.json"):
    import setup as setup
    
class AutocompleteCTkEntry(ctk.CTkEntry):
    def __init__(self, *args, completion_list=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._completion_list = completion_list or []
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        
        self.bind('<Tab>', self.next_option)
        self.bind('<Down>', self.next_option)
        
        self.bind('<Control-Tab>', self.previous_option)
        self.bind('<Shift-Tab>', self.previous_option)
        self.bind('<Up>', self.previous_option)

    def set_completion_list(self, completion_list):
        self._completion_list = completion_list

    def autocomplete(self):
        self.position = len(self.get())
        _hits = []
        for element in self._completion_list:
            if str(element).lower().startswith(self.get().lower()):
                _hits.append(element)

        if _hits != self._hits:
            self._hit_index = 0
            self._hits = _hits

        if self._hits:
            self.delete(0, ctk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, ctk.END)

    def handle_keyrelease(self, event):
        if len(event.keysym) == 1:
            self.autocomplete()
    
    def next_option(self, event):
        self._hit_index = (self._hit_index + 1) % len(self._hits)
        self.delete(0, ctk.END)
        self.insert(0, self._hits[self._hit_index])
        self.select_range(self.position, ctk.END)
    
    def previous_option(self, event):
        self._hit_index = (self._hit_index - 1) % len(self._hits)
        self.delete(0, ctk.END)
        self.insert(0, self._hits[self._hit_index])
        self.select_range(self.position, ctk.END)

class Song:
    def __init__(self, filepath):
        self.filepath = filepath
        try:
            audio = MP3(filepath)
            self.title = audio.get('TIT2', None)
            self.album = audio.get('TALB', None)
            if self.title is None:
                self.title = os.path.basename(filepath).replace(".mp3", "")
        except Exception as e:
            raise ValueError(f"Error reading MP3 metadata from {filepath}: {e}")

class SongFragment:
    def __init__(self, song):
        self.song = song
        self.fragment_data = self.create_fragment()

    def create_fragment(self):
        try:
            song_duration = AudioSegment.from_file(self.song.filepath).duration_seconds
            start_time = random.randint(10, int(song_duration - 20))
            end_time = start_time + 10
            cmd = f'ffmpeg -i "{self.song.filepath}" -ss {start_time} -to {end_time} -c:a libmp3lame data/temp.mp3'
            subprocess.call(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            with open("data/temp.mp3", "rb") as f:
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
                        MP3(os.path.join(root, file))
                        songs.append(Song(os.path.join(root, file)))
                    except:
                        print(f"Error reading {file}, skipping...")
                        messagebox.showerror("Error", f"Error reading {file}, skipping...")
        return songs

    def change_folder(self, new_folder):
        self.songs_dir = new_folder

class SongGuesser:
    def __init__(self, master):
        self.master = master
        self.last_choices = []
        self.num_songs_to_exclude = -10
        master.title("Song Guesser")
        master.resizable(False, False)
        try:
            master.iconbitmap("data/logo.ico")
        except:
            print("Warning: 'data/logo.ico' not found. Icon not set.")
        self.song_library = SongLibrary("music")
        pygame.mixer.init()
        try:
            with open("data/config.json", "r") as f:
                config = json.load(f)
                if "volume" in config:
                    pygame.mixer.music.set_volume(config["volume"] / 100)
                else:
                    pygame.mixer.music.set_volume(1)
        except Exception as e:
            print(f"Error loading config.json: {e}")
            messagebox.showerror("Error", "Error loading configuration. Using default settings.")

        # Appearance settings
        ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

        # Music logo
        self.music_logo_image = ctk.CTkImage(light_image=Image.open("data/banner.png"),
                                  dark_image=Image.open("data/banner_dark.png"),
                                  size=(365, 220))
        self.music_logo_label = ctk.CTkLabel(master, image=self.music_logo_image, text="")
        self.music_logo_label.grid(row=1, column=0, columnspan=2)

        # Buttons
        self.start_button = ctk.CTkButton(master, text="Start", command=self.play_game, width=185, height=40) 
        self.start_button.grid(row=2, column=0, columnspan=1, pady=5, padx=5, sticky="ew") 
        self.options_button = ctk.CTkButton(master, text="Options", command=self.show_buttons_options, width=185, height=40)
        self.options_button.grid(row=2, column=1, columnspan=1, pady=5, padx=5, sticky="ew")

        # Options screen    
        self.sound_slider = ctk.CTkSlider(master, from_=0, to=100)
        self.sound_slider.grid(row=1, column=0, columnspan=2, ipady=10, padx=10, sticky="ew")
        self.sound_slider.configure(command=lambda x: [pygame.mixer.music.set_volume(float(x)/100), self.sound_slider_amount.configure(text=f"Volume: {round(x)}%")])
        self.sound_slider.grid_remove()
        
        self.sound_slider_amount = ctk.CTkLabel(master, text=f"Volume: {round(self.sound_slider.get())}%", width=100, height=40, font=("Arial", 20))
        self.sound_slider_amount.grid(row=0, column=0, columnspan=2)
        self.sound_slider_amount.grid_remove()
        
        self.input_mode_switch = ctk.CTkSwitch(master, text="Input Mode", command=self.toggle_input_mode)
        self.input_mode_switch.grid(row=2, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.input_mode_switch.grid_remove()
        
        self.input_mode = False
        
        self.last_songs_label = ctk.CTkLabel(master, text="Pick how many song backwards do you want to not see while playing:", width=250, height=40)
        self.last_songs_label.grid(row=3, column=0, columnspan=2)
        self.last_songs_label.grid_remove()
        
        self.last_songs_entry = ctk.CTkEntry(master, width=250)
        self.last_songs_entry.grid(row=4, column=0, columnspan=2)
        self.last_songs_entry.grid_remove()
        
        self.last_songs_button = ctk.CTkButton(master, text="Save", command=self.save_picked_number, width=250, height=40) 
        self.last_songs_button.grid(row=5, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.last_songs_button.grid_remove()

        self.download_button = ctk.CTkButton(master, text="Download songs", command=main, width=250, height=40)
        self.download_button.grid(row=6, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.download_button.grid_remove()

        self.folder_select_button = ctk.CTkButton(master, text="Select music folder", command=lambda: [self.song_library.change_folder(filedialog.askdirectory(initialdir = "music")), self.save_game_state()], width=250, height=40)
        self.folder_select_button.grid(row=7, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.folder_select_button.grid_remove()

        self.back_button_opt = ctk.CTkButton(master, text="Back", command=lambda: [self.show_buttons_menu(), self.save_game_state()], width=250, height=40) 
        self.back_button_opt.grid(row=8, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.back_button_opt.grid_remove()

        # Game screen
        self.score = ctk.StringVar()
        self.score.set("0")
        self.score_label = ctk.CTkLabel(master, textvariable=self.score, width=300, height=40)
        self.score_label.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self.score_label.grid_remove()

        self.back_button_game = ctk.CTkButton(master, text="Back", command=lambda: [self.show_buttons_menu(), self.stop_song()], width=100, height=40) 
        self.back_button_game.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        self.back_button_game.grid_remove()

        # Choice Buttons
        self.choices_lock = threading.Lock()
        self.correct_song = None
        self.choices = []
        self.options = [
            ctk.CTkButton(master, text="", command=lambda i=i: self.check_answer(i), width=600, height=40, state=ctk.DISABLED) 
            for i in range(4)
            ]
        for option in self.options:
            option.grid(row=self.options.index(option) + 1, column=0, columnspan=2, pady=5, padx=5)
            option.grid_remove()
        
        # Input mode
        self.song_entry = AutocompleteCTkEntry(self.master, placeholder_text="Enter song title", width=400, completion_list=[])  # Use AutocompleteCTkEntry
        self.confirm_button = ctk.CTkButton(master, text="Confirm", command=self.check_answer_input)
        self.song_entry.grid(row=3, column=0, columnspan=2, pady=5, padx=5)
        self.confirm_button.grid(row=4, column=0, columnspan=2, pady=5, padx=5)
        self.song_entry.grid_remove()
        self.confirm_button.grid_remove()
            
        self.pause_button = ctk.CTkButton(master, text="Pause", command=self.pause_song, state=ctk.DISABLED, width=200, height=40)
        self.pause_button.grid(row=5, column=1, pady=5, padx=5, sticky="ew")
        self.pause_button.grid_remove()

        self.replay_button = ctk.CTkButton(master, text="Replay song", command=self.replay_song, width=300, height=40)
        self.replay_button.grid(row=5, column=0, pady=5, padx=5, sticky="ew")
        self.replay_button.grid_remove()

    def show_buttons_game(self):
        self.start_button.grid_remove()
        self.music_logo_label.grid_remove()
        self.options_button.grid_remove()
        self.replay_button.grid()
        self.score_label.grid()
        for option in self.options:
            option.grid()
        self.pause_button.grid()
        self.back_button_game.grid()
    
    def show_buttons_game_input_mode(self):
        self.start_button.grid_remove()
        self.music_logo_label.grid_remove()
        self.options_button.grid_remove()
        self.replay_button.grid()
        self.score_label.grid()
        self.song_entry.grid()
        self.confirm_button.grid()
        self.back_button_game.grid()
        self.pause_button.grid()

    def show_buttons_menu(self):
        self.back_button_opt.grid_remove()
        self.back_button_game.grid_remove()
        self.score_label.grid_remove()
        for option in self.options:
            option.grid_remove()
        self.pause_button.grid_remove()
        self.sound_slider.grid_remove()
        self.replay_button.grid_remove()
        self.folder_select_button.grid_remove()
        self.download_button.grid_remove()
        self.last_songs_button.grid_remove()
        self.last_songs_entry.grid_remove()
        self.last_songs_label.grid_remove()
        self.sound_slider_amount.grid_remove()
        self.input_mode_switch.grid_remove()
        self.song_entry.grid_remove()
        self.confirm_button.grid_remove()
        self.start_button.grid()
        self.music_logo_label.grid()
        self.options_button.grid()

    def show_buttons_options(self):
        self.start_button.grid_remove()
        self.music_logo_label.grid_remove()
        self.options_button.grid_remove()
        self.sound_slider.grid()
        self.back_button_opt.grid()
        self.folder_select_button.grid()
        self.download_button.grid()
        self.last_songs_label.grid()
        self.last_songs_entry.grid()
        self.last_songs_button.grid()
        self.sound_slider_amount.grid()
        self.input_mode_switch.grid()
    
    def play_game(self):
        self.show_buttons_game_input_mode() if self.input_mode else self.show_buttons_game()
        self.play_song()
        
    def toggle_input_mode(self):
        self.input_mode = self.input_mode_switch.get()

    def get_song_suggestions(self, text):
        suggestions = []
        for song in self.song_library.get_songs():
            if text.lower() in song.title.lower():
                suggestions.append(song.title)
        return suggestions

    def check_answer_input(self):
        entered_title = self.song_entry.get()
        correct_song = str(self.correct_song.title)
        correct_song = correct_song.split(" - ")[0]
        if entered_title.lower() == correct_song.lower():
            self.score.set(str(int(self.score.get()) + 1))
            pygame.mixer.music.stop()
            pygame.mixer.music.load("data/correct.mp3")
            pygame.mixer.music.set_volume(0.1)
            pygame.mixer.music.play()
            with open("data/config.json", "r") as f:
                config = json.load(f)
                if "volume" in config:
                    pygame.mixer.music.set_volume(config["volume"] / 100)
                else:
                    pygame.mixer.music.set_volume(1)
            root.update_idletasks()
        else:
            print(f"Wrong! The correct answer was {self.correct_song.title}")
            messagebox.showinfo("Wrong!", f"The correct answer was {self.correct_song.title}")
        self.last_choices.append(self.correct_song)
        self.play_song()
        
    def save_num_songs_to_exclude(self):
        self.num_songs_to_exclude = int("-" + self.last_songs_entry.get())
    
    def save_picked_number(self):
        try:
            picked_number = int("-" + self.last_songs_entry.get())
            if picked_number >= 0:
                raise ValueError("Number of songs to exclude must be positive.")
            self.picked_number = picked_number
            self.save_num_songs_to_exclude()
            messagebox.showinfo("Success", f"Number of songs to exclude set to {picked_number}.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a positive integer for the number of songs to exclude.")

    def save_game_state(self):
        game_state = {
            "volume": round(self.sound_slider.get())
        }

        with open("data/config.json", "w") as f:
            json.dump(game_state, f)

    def get_random_choices(self, songs, correct_song):
        choices = [correct_song]
        while len(choices) < 4:
            random_song = random.choice(songs)
            if not any(c.title == random_song.title and c.album == random_song.album for c in choices):
                choices.append(random_song)
        random.shuffle(choices)
        return choices

    def check_answer(self, choice_index):
        with self.choices_lock:
            if self.choices[choice_index] == self.correct_song:
                self.score.set(str(int(self.score.get()) + 1))
                pygame.mixer.music.stop()
                pygame.mixer.music.load("data/correct.mp3")
                pygame.mixer.music.set_volume(0.1)
                pygame.mixer.music.play()
                with open("data/config.json", "r") as f:
                    config = json.load(f)
                    if "volume" in config:
                        pygame.mixer.music.set_volume(config["volume"] / 100)
                    else:
                        pygame.mixer.music.set_volume(1)
                root.update_idletasks()
            else:
                print(f"Wrong! The correct answer was {self.correct_song.title}")
                messagebox.showinfo("Wrong!", f"The correct answer was {self.correct_song.title}")
        self.last_choices.append(self.correct_song)
        self.play_song()

    def update_options(self):
        new_choices = self.get_random_choices(self.song_library.get_songs(), self.correct_song)
        with self.choices_lock:
            self.choices = new_choices
        for i, choice in enumerate(self.choices): 
            self.options[i].configure(text=f"{choice.title}   ({choice.album})" if choice.album or choice.album != None else choice.title)
       
    def play_song(self):
        if os.path.exists("data/temp.mp3"):
            os.remove("data/temp.mp3")
        songs = self.song_library.get_songs()
        if not songs:
            print("No valid MP3 files found in the selected directory.")
            messagebox.showerror("Error", "No valid MP3 files found in the selected directory.")
            return

        random.seed(int(time.time() * 1000))
        self.correct_song = random.choice(songs)
        if self.correct_song in self.last_choices[-self.num_songs_to_exclude:]:
            self.correct_song = random.choice(songs)

        threading.Thread(target=self.update_options).start()
        
        if self.input_mode:
            self.song_entry.set_completion_list([song.title for song in self.song_library.get_songs()])
        
        try:
            song_fragment = SongFragment(self.correct_song)
            fragment = song_fragment.fragment_data
            if fragment:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    temp_filename = f.name
                    f.write(fragment)
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()
                self.pause_button.configure(state=ctk.NORMAL)
                for option in self.options:
                    option.configure(state=ctk.NORMAL)
            else:
                print(f"Error playing {self.correct_song.filepath}. Skipping...")
        except Exception as e:
            print(f"Error playing song: {e}")
            messagebox.showerror("Error", "Error playing song.")

    def pause_song(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.pause_button.configure(text="Resume")
        else:
            pygame.mixer.music.unpause()
            self.pause_button.configure(text="Pause")

    def replay_song(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.play()
    
    def stop_song(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
root = ctk.CTk()
guesser = SongGuesser(root)
root.mainloop()
pygame.mixer.quit() 