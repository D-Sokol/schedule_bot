notify-unknown_intent = This button is too old. I don't even remember what we were talking about!
notify-not_implemented = This feature will be added later. Sorry.


notify-saved_image =
    Background saved!
    <b>{ $escaped_name }</b>


notify-name_used =
    The name <b>{ $escaped_name }</b> cannot be used: it's already taken!


notify-remove_image = Image <b>{ $escaped_name }</b> has been deleted


# No HTML markup available here
notify-reorder = Unused
    .first = { $name } is now at the top of the list!
    .last = { $name } is now at the bottom of the list!


notify-templates = Unused
    .error_json = Failed to read the uploaded file
    .error_validation = The uploaded file doesn't look like a template
    .old_filename = Previous template.json
    .old_description = Just in case, here's the previous template!
    .local_filename = Template.json
    .local_description = The template that will be used now
    .global_filename = Default template.json
    .global_description = Standard default template


notify-forbidden = This feature is only available to administrators.


notify-help =
    This bot allows you to create a weekly schedule as an image.
    Overlay images and captions are placed on a specified background according to the schedule and template—either uploaded or provided by default.

    The source code is distributed under the GNU AGPLv3 license and is available <a href="{ $source_code_url }">here</a>.


notify-admin = Unused
    .grant = Administrator { $user_id } has been assigned
    .revoke = Administrator { $user_id } has been removed
    .ban = User { $user_id } has been banned
    .unban = User { $user_id } has been unbanned


notify-wizard-print =
    Here's what the entered schedule looks like as text:
    <i>{ $schedule }</i>
