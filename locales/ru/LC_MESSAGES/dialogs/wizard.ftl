dialog-wizard-start = Здесь вы можете отредактировать расписание
    .n_tags = {
        $n_tags ->
        [0] (нет тегов)
        [one] (1 тег)
        [few] ({ $n_tags } тега)
        *[many] ({ $n_tags } тегов)
    }
    .clone = 🆕
    .remove = 🚮️
    .new = 🆕 Добавить
    .sort = 🔡 Упорядочить
    .print = 📝 В текст
    .confirm = ✅ Готово


dialog-wizard-dow =
    На какой день недели поставить запись?
    Сейчас: <i>{
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
    На какое время поставить запись?
    Сейчас: <i>{ $current_time }</i>

    .back = { dialog-back }


dialog-wizard-tags =
    Какие теги должны быть у записи?
    Сейчас: {
        $n_tags ->
        [0] <i>нет</i>
        *[other] <i>{ $current_tags }</i>
    }

    .clear = 🧹 Удалить все теги
    .back = { dialog-back }


dialog-wizard-desc =
    Какое описание должно быть у записи?
    Сейчас: <i>{ $current_desc }</i>

    .back = { dialog-back }
