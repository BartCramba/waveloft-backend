from mutagen.flac import FLAC

def extract_album_art(file_path):
    audio = FLAC(file_path)
    if "metadata_block_picture" in audio:
        for picture in audio.pictures:
            print(f"Found album art: MIME type: {picture.mime}, Size: {len(picture.data)} bytes")
            # Save the artwork for debugging purposes
            with open("album_art.jpg", "wb") as f:
                f.write(picture.data)
            return picture.data
    else:
        print("No album art found in metadata_block_picture.")
    return None




if __name__ == '__main__':

    # Example usage
    album_art = extract_album_art("C:\\stuff\\projects\\demo-app\\tests\\Vitess - Hotline.flac")
    if album_art:
        print("Album art successfully extracted!")
    else:
        print("No album art available.")
