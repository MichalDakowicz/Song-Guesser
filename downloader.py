import customtkinter as ctk
import os
import threading

def download_song(song_link):
    os.system(f'python -m spotdl {song_link}')

def download(download_folder, links_field):
    if not os.path.exists(f'music/{download_folder.get()}'):
        os.mkdir(f'music/{download_folder.get()}')
    os.chdir(f'music/{download_folder.get()}')
    threads = []
    for line in links_field.get('1.0', ctk.END).split():
        thread = threading.Thread(target=download_song, args=(line,))
        thread.start()
        threads.append(thread)

        for thread in threads:
            thread.join()

def main():
    downloader_root = ctk.CTk()
    
    downloader_root.title('Spotify Downloader')
    downloader_root.geometry('500x400')

    downloader_root.iconbitmap('data/downloader.ico')
    
    downloader_info = ctk.CTkLabel(downloader_root, text='Spotify Downloader. Please be patient during the download process.', font=('Arial', 12))
    downloader_info.pack(pady=10)

    info_label = ctk.CTkLabel(downloader_root, text='Enter the download folder name:')
    info_label.pack(pady=10)
    
    download_folder = ctk.CTkEntry(downloader_root, width=200)
    download_folder.pack(pady=10)

    links_info = ctk.CTkLabel(downloader_root, text='Enter the Spotify links (one per line):')
    links_info.pack(pady=10)

    links_field = ctk.CTkTextbox(downloader_root, height=120, width=300)
    links_field.pack(pady=10)

    download_button = ctk.CTkButton(downloader_root, text='Download', command=lambda: download(download_folder, links_field))
    download_button.pack(pady=10)

    downloader_root.mainloop()
