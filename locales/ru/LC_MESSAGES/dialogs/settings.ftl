dialog-settings =
    Выбор языка и настроек интерфейса.

    .apply = 💾 Сохранить
    .confirm = ✅ Готово
    .accept_uncompressed_checked = 🔄 Настаивать на отправке файлом: Нет
    .accept_uncompressed_unchecked = 📌 Настаивать на отправке файлом: Да

    .language =
        {
            $checked ->
            *[0] ⚪️
            [1] 🔘
        } {
            $language ->
            [en] English 🇺🇸
            [ru] Русский 🇷🇺
            *[other] Неизвестно 🌐
        }
