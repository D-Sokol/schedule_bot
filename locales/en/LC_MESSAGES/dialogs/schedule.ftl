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
