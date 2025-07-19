dialog-upload-main =
    Upload an image to use as background.
    I recommend sending it as file to avoid quality loss!


dialog-upload-nodoc =
    You didn't send the image as file. This may cause quality loss. Want to upload it again?


dialog-upload-dim =
    Uploaded image dimensions ({ $real_width }x{ $real_height })
    differ from expected ({ $expected_width }x{ $expected_height })
    You can upload another image or use this one anyway.

    .resize = Stretch to required size
    .crop = Crop image


dialog-upload-name =
    Enter a name for this image to recognize it later!
    By default it will be named { $automatic_name }.


dialog-upload-fail = {
    $reason ->
    [file_size]
        This file is too big. Maybe it's not even an image.
        Background can't be saved.
    [unreadable]
        Failed to open the sent file as image.
        Background can't be saved.
    *[other]
        Background can't be saved.
    }

    .accept = Accept
