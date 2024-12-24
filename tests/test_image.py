import os

from mutagen import File
import tempfile


def debug_album_art(file_path):
    """
    Debug and extract album art locally from an audio file using Mutagen.
    """
    print(f"Analyzing file: {file_path}")

    # Load the audio file with Mutagen
    audio = File(file_path, easy=False)  # Use `easy=False` to access raw tags
    if not audio:
        print("Failed to load the file. Unsupported or invalid audio format.")
        return

    print("Audio metadata and tags:")
    for tag_key, tag_value in audio.tags.items():
        print(f"  Tag: {tag_key} - Value: {tag_value}")

    # Check for album art
    print("\nSearching for album art...")
    found_album_art = False
    if hasattr(audio, "tags") and audio.tags:
        for tag_key, tag_value in audio.tags.items():
            # Check for MP3/APIC album art
            if tag_key.startswith("APIC"):
                found_album_art = True
                print(f"Found album art in APIC tag: {tag_key}")
                save_album_art_locally(tag_value.data, "album_art_from_apic.jpg")

            # Check for FLAC/PICTURE album art
            if hasattr(tag_value, "data"):  # Ensure the tag contains picture data
                found_album_art = True
                print(f"Found album art in PICTURE tag: {tag_key}")
                save_album_art_locally(tag_value.data, f"album_art_{tag_key}.jpg")

    if not found_album_art:
        print("No album art found in the file.")


def save_album_art_locally(data, file_name):
    """
    Save album art data to a local file.
    """
    file_path = os.path.join(tempfile.gettempdir(), file_name)
    with open(file_path, "wb") as album_art_file:
        album_art_file.write(data)
    print(f"Album art saved locally as: {file_path}")


# Test the function
if __name__ == "__main__":
    # Replace this with the path to your audio file
    file_path = "C:\\stuff\\projects\\demo-app\\tests\\Vitess - Hotline.flac"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
    else:
        debug_album_art(file_path)