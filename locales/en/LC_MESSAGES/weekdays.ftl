weekdays-d1 = Mon
    .alias1 = Monday

weekdays-d2 = Tue
    .alias1 = Tuesday

weekdays-d3 = Wed
    .alias1 = Wednesday

weekdays-d4 = Thu
    .alias1 = Thursday

weekdays-d5 = Fri
    .alias1 = Friday

weekdays-d6 = Sat
    .alias1 = Saturday
    .alias2 = Caturday

weekdays-d7 = Sun
    .alias1 = Sunday


weekdays-by_id = {
    $day ->
    *[1] { weekdays-d1 }
    [2] { weekdays-d2 }
    [3] { weekdays-d3 }
    [4] { weekdays-d4 }
    [5] { weekdays-d5 }
    [6] { weekdays-d6 }
    [7] { weekdays-d7 }
}
