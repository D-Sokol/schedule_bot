dialog-cancel = ❌ Отставеть!
dialog-fine = И так сойдет
dialog-back = Назад

dialog-main = Выберите действие!
    .backgrounds-local = Фоновые изображения
    .create = Создать расписание
    .templates = Шаблон расписания
    .backgrounds-global = Накладываемые элементы


dialog-backgrounds-main = Unused
    .number = {
        $n_backgrounds ->
        [0] У вас нет сохраненных фоновых изображений.
        [one] Вы сохранили { $n_backgrounds } фоновое изображение. Вы можете выбрать фон, нажав на его название.
        [few] Вы сохранили { $n_backgrounds } фоновых изображения. Вы можете выбрать фон, нажав на его название.
        *[many] Вы сохранили { $n_backgrounds } фоновых изображений. Вы можете выбрать фон, нажав на его название.
    }
    .limit = Достигнут предел количества сохраненных изображений ({ $limit }).
    .item = 🖼️ { $item_name }
    .upload = Загрузить фон


dialog-backgrounds-selected = <b>{ $escaped_name }</b>
    .create = { dialog-main.create }
    .rename = Переименовать
    .full = 📄️ Прислать без сжатия
    .delete = 🚮️ Удалить
    .old = 🌖️ В конец списка
    .new = 🌒️ В начало списка
    .back = { dialog-back }


dialog-backgrounds-rename =
    Введите новое имя для изображения (до 50 символов)

    .cancel = { dialog-cancel }


dialog-backgrounds-delete = Точно удалить <b>{ $escaped_name }</b>?
    .confirm = Туда его!
    .cancel = { dialog-cancel }


dialog-upload-main =
    Загрузите изображение для использования в качестве фона.
    Советую отправить картинку как файл, чтобы избежать потери качества!


dialog-upload-nodoc =
    Вы отправили картинку не как файл. Это может привести к потере качества. Можете загрузить картинку еще раз?


dialog-upload-dim =
    Размер загруженного изображения ({ $real_width }x{ $real_height })
    отличается от ожидаемого ({ $expected_width }x{ $expected_height })
    Вы можете загрузить другую картинку или все равно использовать эту.

    .resize = Растянуть до нужного размера
    .crop = Обрезать картинку


dialog-upload-name =
    Введите имя для этой картинки, чтобы потом узнать ее в списке!
    По умолчанию картинка будет называться { $automatic_name }.


dialog-upload-fail = {
    $reason ->
    [file_size]
        Размер этого файла слишком большой. Возможно, это и не картинка вовсе.
        Фон не может быть сохранен.
    [unreadable]
        Не удалось открыть присланный файл как изображение.
        Фон не может быть сохранен.
    *[other]
        Фон не может быть сохранен.
}
    .accept = Смириться


dialog-schedule-main =
    Начинаю создавать расписание.
    Для создания расписания нужно выбрать фон из списка сохраненных изображений или загрузить новый.
    .select = Выбрать фон
    .upload = Загрузить новый фон


dialog-schedule-text = Unused
    .presented =
        Введите текст расписания.
        Вот предыдущее использованное вами расписание:
        <i>{ $user_last_schedule }</i>
    .missing =
        Введите текст расписания.
        Вот простой пример расписания:
        <i>{ $global_last_schedule }</i>
    .example =
        Пн 10:00 Бег
        Пн 11:30 Отжимания
        Пт 18:00 Сходить в бар


dialog-schedule-date = Выберите, на какие даты будет составлено расписание.
    .this = Эта неделя
    .next = Следующая неделя
    .custom = Другая дата


dialog-schedule-calendar = Выберите дату
    .back = ❌ { dialog-back }


dialog-schedule-finish = Спасибо! Расписание готовится...
    .return = Хорошо
