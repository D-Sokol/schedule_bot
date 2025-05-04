weekdays-d1 = пн
    .alias1 = понедельник

weekdays-d2 = вт
    .alias1 = вторник

weekdays-d3 = ср
    .alias1 = среда

weekdays-d4 = чт
    .alias1 = четверг

weekdays-d5 = пт
    .alias1 = пятница

weekdays-d6 = сб
    .alias1 = суббота
    .alias2 = субкота

weekdays-d7 = вс
    .alias1 = воскресенье


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
