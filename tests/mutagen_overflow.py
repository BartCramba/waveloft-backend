from mutagen.id3 import ID3


from mutagen.flac import FLAC

if __name__ == "__main__":
    # Load the FLAC file
    audio = FLAC(r"C:\stuff\projects\demo-app\tests\Vitess - Hotline.flac")

    # Check for album art
    if audio.pictures:
        for picture in audio.pictures:
            print(f"Found album art: MIME type: {picture.mime}, Size: {len(picture.data)} bytes")
            # Save the album art locally
            with open("album_art.jpg", "wb") as f:
                f.write(picture.data)
            print("Album art saved as 'album_art.jpg'")
    else:
        print("No album art found in the FLAC file.")