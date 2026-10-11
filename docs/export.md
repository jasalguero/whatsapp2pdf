# Export a chat from WhatsApp

WhatsApp can export a single chat as a `.txt` file. When you include media, the export is a `.zip` holding the text plus the photos and files. whatsapp2pdf reads either.

=== "Android"

    1. Open the chat.
    2. Tap **⋮** (top right) → **More** → **Export chat**.
    3. Choose **Include media** (photos appear in the PDF) or **Without media** (smaller; media shows as "not included").
    4. Save the file to your device or send it to yourself, e.g. by email or to a cloud drive.

=== "iPhone"

    1. Open the chat and tap the contact or group name at the top.
    2. Scroll down and tap **Export Chat**.
    3. Choose **Attach Media** or **Without Media**.
    4. Pick **Save to Files**, or AirDrop it to your Mac.

!!! note
    WhatsApp limits how much media fits into one export, and very long chats may be cut short on some phones. Media that wasn't included shows up in the PDF as "Media not included in export".

## What's inside

```
WhatsApp Chat - Family.zip
├── _chat.txt                              # iPhone (Android: "WhatsApp Chat with Family.txt")
├── 00000012-PHOTO-2026-03-14-10-02-11.jpg
└── ...
```

You don't need to unzip it; pass the `.zip` straight to `whatsapp2pdf`. If you did unzip it, pass the `.txt` and keep the media files next to it.

!!! warning "These files are private"
    An export holds your whole conversation, including other people's messages and photos. Keep it somewhere safe, and delete it when you're done.
