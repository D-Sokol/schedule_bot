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
    .not_ready = <i>Изображение не может быть показано, т.к. находится в процессе обработки</i>
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
