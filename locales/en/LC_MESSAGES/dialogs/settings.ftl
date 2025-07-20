dialog-settings =
    Language and interface settings.

    .apply = 💾 Apply
    .confirm = ✅ Save and exit
    .accept_uncompressed_checked = 🔄 Insist on sending as a file: No
    .accept_uncompressed_unchecked = 📌 Insist on sending as a file: Yes

    .language =
        {
            $checked ->
            *[0] ⚪️
            [1] 🔘
        } {
            $language ->
            [en] English 🇺🇸
            [ru] Русский 🇷🇺
            *[other] Unknown 🌐
        }
