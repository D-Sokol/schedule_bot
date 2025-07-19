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
