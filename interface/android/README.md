# Aura Android Interface

This package contains the Android visual shell for Aura.

The implementation uses Kivy when available and calls the shared Aura backend
services directly through the runtime context:

- `context.interpreter` and `context.intentRouter` for chat
- `context.reminders` for reminder creation and listing
- `context.notifications` for notification listing
- `context.calendar` for calendar day views and event creation

Importing the package does not require Kivy. Running `AuraAndroidApp.run()`
requires Kivy to be installed in the Android build environment.
