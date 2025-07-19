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
