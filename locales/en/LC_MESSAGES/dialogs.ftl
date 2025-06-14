dialog-cancel = ❌ Leave me alone!
dialog-fine = Good enough
dialog-back = ⬅️ Back

dialog-main = Choose an action!
    .backgrounds-local = Background images
    .create = Create schedule
    .templates = Schedule template
    .backgrounds-global = Overlay elements
    .admin = Admin stuff
    .settings = Settings


dialog-backgrounds-main = Unused
    .number = {
        $n_backgrounds ->
        [0] You have no saved background images.
        [one] You have { $n_backgrounds } background image saved. You can select a background by clicking its name.
        *[many] You have { $n_backgrounds } background images saved. You can select a background by clicking its name.
    }
    .limit = Maximum number of saved images reached ({ $limit }).
    .item = 🖼️ { $item_name }
    .upload = Upload background


dialog-backgrounds-selected = <b>{ $escaped_name }</b>
    .not_ready = <i>Image can't be displayed as it's being processed</i>
    .create = { dialog-main.create }
    .rename = Rename
    .full = 📄 Send uncompressed
    .delete = 🚮 Delete
    .old = 🌖 Move to end
    .new = 🌒 Move to beginning
    .back = { dialog-back }


dialog-backgrounds-rename =
    Enter new name for the image (up to 50 characters)

    .cancel = { dialog-cancel }


dialog-backgrounds-delete = Really delete <b>{ $escaped_name }</b>?
    .confirm = Delete it!
    .cancel = { dialog-cancel }


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


dialog-schedule-main =
    Starting schedule creation.
    To create schedule you need to select background from saved images or upload new one.
    .select = Select background
    .upload = Upload new background


dialog-schedule-text = Unused
    .presented =
        Enter schedule text.
        Here's your last used schedule:
        <i>{ $user_last_schedule }</i>
    .missing =
        Enter schedule text.
        Here's a simple example:
        <i>{ $global_last_schedule }</i>
    .example =
        Mon 10:00 (important) Running
        Mon 11:30 (important) Push-ups
        Fri 18:00 Go to bar
    .accept_previous = Use previous
    .wizard = Open editor
    .back = { dialog-back }
    .warn_empty = <b>Can't create schedule</b>: no items
    .warn_unparsed = <b>Following lines weren't understood and were excluded from schedule</b>:


dialog-schedule-date = Choose dates for the schedule.
    .this = This week
    .next = Next week
    .custom = Other date
    .back = { dialog-back }


dialog-schedule-calendar = Choose date
    .back = { dialog-back }


dialog-schedule-finish = Thanks! Schedule is being prepared...
    .return = OK


dialog-wizard-start = Here you can edit the schedule
    .n_tags = {
        $n_tags ->
        [0] (no tags)
        [one] (1 tag)
        *[many] ({ $n_tags } tags)
    }
    .clone = 🆕
    .remove = 🚮
    .new = 🆕 Add
    .sort = 🔡 Sort
    .print = 📝 To text
    .confirm = ✅ Done


dialog-wizard-dow =
    Which weekday for the entry?
    Current: <i>{
    $current_day ->
    *[1] { weekdays-d1 }
    [2] { weekdays-d2 }
    [3] { weekdays-d3 }
    [4] { weekdays-d4 }
    [5] { weekdays-d5 }
    [6] { weekdays-d6 }
    [7] { weekdays-d7 }
    }</i>

    .back = { dialog-back }


dialog-wizard-time =
    What time for the entry?
    Current: <i>{ $current_time }</i>

    .back = { dialog-back }


dialog-wizard-tags =
    What tags should the entry have?
    Current: {
        $n_tags ->
        [0] <i>none</i>
        *[other] <i>{ $current_tags }</i>
    }

    .clear = 🧹 Clear all tags
    .back = { dialog-back }


dialog-wizard-desc =
    What description should the entry have?
    Current: <i>{ $current_desc }</i>

    .back = { dialog-back }


dialog-templates =
    Templates define schedule appearance and overlay elements set.
    {
        $has_local ->
        *[0]
            Default template is used by default. You can upload your own template by sending it as file.
        [1]
            You're using custom template. You can upload new one by sending it as file.
    }

    .view_user = Download your template
    .view_global = Download default template
    .clear = Remove your template


dialog-admin-main = Bot administration functions
    .plus-admin = Make admin
    .minus-admin = Remove admin
    .plus-ban = Ban
    .minus-ban = Unban


dialog-users = Specify user by forwarding any their message or entering account ID (as number)
    .hidden_user =
        Forwarded message must be from person, not chat or bot.
        Also account shouldn't be hidden by privacy settings when forwarding.
    .unparseable_text =
        To specify ID you need to enter single positive number.
        Account ID display can be enabled in experimental settings on desktop clients.
