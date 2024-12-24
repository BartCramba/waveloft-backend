import mimetypes



if __name__ == '__main__':
    # List all MIME types and their extensions
    print("Supported MIME Types:")
    for mime, ext in mimetypes.types_map.items():
        print(f"{ext}: {mime}")


    # Check if specific MIME types are supported
    def check_mime_type(mime):
        extensions = [ext for ext, mt in mimetypes.types_map.items() if mt == mime]
        if extensions:
            print(f"MIME type '{mime}' is supported with extensions: {extensions}")
        else:
            print(f"MIME type '{mime}' is NOT supported.")


    # Examples to check specific MIME types
    check_mime_type("audio/flac")
    check_mime_type("audio/mpeg")
    check_mime_type("audio/wav")
    check_mime_type("audio/x-m4a")