notify-unknown_intent = Эта кнопка слишком старая. Я даже не помню, о чем мы говорили!
notify-not_implemented = Этот функционал будет добавлен в дальнейшем. Извините.


notify-saved_image =
    Фон сохранен!
    <b>{ $escaped_name }</b>


notify-name_used =
    Использовать имя <b>{ $escaped_name }</b> невозможно: оно уже используется!


notify-remove_image = Изображение <b>{ $escaped_name }</b> удалено


# No HTML markup available here
notify-reorder = Unused
    .first = Теперь { $name } находится в начале списка!
    .last = Теперь { $name } находится в конце списка!


notify-templates = Unused
    .error_json = Не удалось прочитать присланный файл
    .error_validation = Присланный файл не выглядит как шаблон
    .old_filename = Предыдущий шаблон.json
    .old_description = На всякий случай отправляю предыдущий шаблон!
    .local_filename = Шаблон.json
    .local_description = Шаблон, который будет использоваться сейчас
    .global_filename = Общий шаблон.json
    .global_description = Стандартный шаблон по умолчанию


notify-forbidden = Этот функционал доступен только для администраторов.


notify-help =
    Этот бот позволяет создать расписание на неделю в виде картинки.
    На заданный фон накладываются изображения и подписи в соответствии с расписанием и шаблоном - загруженным или предоставленным по умолчанию.

    Исходный код распространяется под лицензией GNU AGPLv3 и доступен <a href="{ $source_code_url }">здесь</a>.


notify-admin = Unused
    .grant = Администратор { $user_id } назначен
    .revoke = Администратор { $user_id } удален
    .ban = Пользователь { $user_id } забанен
    .unban = Пользователь { $user_id } амнистирован


notify-wizard-print =
    Вот так выглядит введенное расписание в виде текста:
    <i>{ $schedule }</i>
