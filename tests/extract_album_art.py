import os
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

def extract_album_art_to_local(file_path, output_dir="album_art"):
    """
    Extract album art from an audio file (MP3 or FLAC) and save it locally.
    Args:
        file_path (str): Path to the audio file.
        output_dir (str): Directory to save the album art.
    Returns:
        str: Local path to the saved album art, or None if no album art found.
    """
    album_art_path = None
    file_extension = os.path.splitext(file_path)[1].lower()

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    try:
        if file_extension == '.mp3':
            # Extract album art from MP3
            audio = MP3(file_path, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):  # MP3 album art
                    album_art_path = os.path.join(output_dir, f"album_art_{os.path.basename(file_path)}.jpg")
                    with open(album_art_path, 'wb') as img:
                        img.write(tag.data)
                    print(f"Album art extracted and saved locally: {album_art_path}")
                    break
        elif file_extension == '.flac':
            # Extract album art from FLAC
            audio = FLAC(file_path)
            for picture in audio.pictures:
                album_art_path = os.path.join(output_dir, f"album_art_{os.path.basename(file_path)}.{picture.mime.split('/')[-1]}")
                with open(album_art_path, 'wb') as img:
                    img.write(picture.data)
                print(f"Album art extracted and saved locally: {album_art_path}")
                break

        if not album_art_path:
            print("No album art found in the audio file.")
            return None

        return album_art_path
    except Exception as e:
        print(f"Error extracting album art: {e}")
        return None

if __name__ == '__main__':
    # extract_album_art_to_local("C:\\stuff\\projects\\demo-app\\tests\\Vitess - Hotline.flac")
    extract_album_art_to_local("C:\\stuff\\projects\\demo-app\\tests\\All Saints - Pure Shores (Fyrone Edit).mp3")
