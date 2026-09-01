# IntenType Demo Video Script

**Target length:** 90 seconds  
**No voiceover needed** — on-screen text cards tell the story  
**Tool:** QuickTime → New Screen Recording  
**Export:** 1080p H.264, save as `docs/demo.mp4`

---

## Before you hit record

- [ ] Set wallpaper to solid black (System Settings → Wallpaper → Color → Black)
- [ ] Hide Dock (auto-hide on)
- [ ] Turn on Do Not Disturb
- [ ] Have these apps ready (don't open yet): Notes, Microsoft Teams or WhatsApp Web, Google Chrome
- [ ] Have the IntenType landing page open in Safari/Chrome
- [ ] Have the DMG file downloaded and ready (or drag from `dist/`)
- [ ] Delete any existing IntenType from Applications before recording
- [ ] Kill any running IntenType daemon: `killall -9 Python 2>/dev/null; true`

---

## PART 1 — Download (0:00–0:12)

**Screen:** IntenType landing page open in browser

**Action:** Slowly scroll down the page for 2–3 seconds so viewer sees the product headline.

**Text card (bottom):**
> IntenType — voice typing with AI polish for Mac

**Action:** Scroll back up to the Download button. Move cursor to it. Pause 1 second.

**Action:** Click **Download for Mac — Free**

**Action:** Show the DMG file downloading in the browser download bar (bottom or top right). Wait for it to finish.

**Text card:**
> Step 1 — Download

---

## PART 2 — Install (0:12–0:28)

**Action:** Click the downloaded DMG to open it. The DMG window opens showing IntenType.app and the Applications folder shortcut.

**Text card:**
> Step 2 — Drag to Applications

**Action:** Drag IntenType.app to the Applications folder arrow. Wait for copy to finish.

**Action:** Eject the DMG (drag to Trash or right-click → Eject).

**Action:** Open Applications folder in Finder. Double-click IntenType.

**Action:** macOS Gatekeeper dialog appears — click **Open** (right-click → Open the first time).

---

## PART 3 — First launch & API key (0:28–0:50)

**Action:** IntenType launches. After 1–2 seconds, the **"Connect to OpenAI"** dialog appears automatically.

**Text card:**
> Step 3 — Paste your OpenAI key  
> (one-time setup)

**Action:** Click into the text field in the dialog.

**Action:** Paste an API key (`sk-proj-...`) using Cmd+V. The field fills.

**Action:** Click **Save**.

**Text card:**
> That's it. IntenType is ready.

**Action:** Show the IntenType menubar icon (top-right of screen). Move cursor to hover over it briefly.

---

## PART 4 — Use it anywhere (0:50–1:30)

This is the core of the video. Show the same 3-step gesture in 4 different apps back-to-back.

---

### App 1 — Apple Notes (0:50–1:02)

**Action:** Open Notes. Click into an empty note. Cursor is blinking.

**Text card:**
> Hold ⌥ Right Option → speak → release

**Action:** Press and **hold** the Right Option key.

*(The waveform pill appears at top center of screen — pause 0.5s so viewer notices it)*

**Speak naturally:**
> "hey just wanted to remind you that the team meeting tomorrow is moved to 3pm, please update your calendar"

**Action:** Release Right Option.

*(1–2 second pause while GPT processes)*

**Text appears in Notes:**
> "Hey, just a reminder that tomorrow's team meeting has been moved to 3 PM. Please update your calendar."

**Text card:**
> Filler words gone. Grammar fixed.

---

### App 2 — Microsoft Teams / WhatsApp Web (1:02–1:14)

**Action:** Cmd+Tab to Teams (or open WhatsApp Web in Chrome). Click into a chat message compose box.

**Action:** Hold Right Option. Waveform pill appears.

**Speak:**
> "uh can you share the final presentation deck before end of day I need to review it before the client call"

**Release.**

**Text appears:**
> "Can you share the final presentation deck before end of day? I need to review it before the client call."

**Text card:**
> Works in Teams, Slack, WhatsApp — any chat app.

---

### App 3 — Google Search (1:14–1:22)

**Action:** Cmd+Tab to Chrome. Click the Google search bar.

**Action:** Hold Right Option. Waveform pill appears.

**Speak:**
> "best coffee shops in San Francisco with outdoor seating"

**Release.**

**Text appears in search bar:**
> "best coffee shops in San Francisco with outdoor seating"

*(No GPT rewrite needed for search — it pastes the clean transcript directly)*

**Text card:**
> Even works in search bars and browsers.

---

### App 4 — VS Code / Any text editor (1:22–1:30)

**Action:** Switch to VS Code (or TextEdit). Click into a comment line.

**Action:** Hold Right Option. Speak:
> "this function handles user authentication and returns a JWT token on success"

**Release.**

**Text appears:**
> "This function handles user authentication and returns a JWT token on success."

---

## END CARD (1:30–1:45)

**Action:** Screen fades to solid black.

**Show (centered, white text, fade in):**

```
IntenType

Hold. Speak. Done.

Free & open source
github.com/shankarswamy294/IntenType
```

**Hold for 5 seconds. Fade out.**

---

## Recording tips

| | |
|---|---|
| **Waveform pill** | Make sure it's visible — it appears at top center. Zoom recording area to 80% of screen width centered so the pill is obvious |
| **Pace** | Go SLOW. Let every output sit for 2 full seconds before moving on |
| **Re-take trigger** | If GPT output looks robotic or wrong, stop and re-record that clip |
| **Cursor size** | Accessibility → Display → Pointer → bump size up one notch |
| **Font size** | If using Notes, bump font to 18pt so output is readable in video |
| **Each app** | Full screen each app before recording that clip — no window chrome distractions |

---

## Post-production (iMovie, 10 min)

1. Import your screen recording
2. Cut clips together in order (Parts 1–4)
3. Add text cards as **Lower Third** titles — white text, no background, SF Pro Display font
4. Trim dead air: keep all pauses under 1 second except after GPT outputs (keep 2s there)
5. Optional: add soft background music (search "minimal focus" in YouTube Audio Library)
6. Export: 1080p → H.264 → **Better Quality**
7. Save as `docs/demo.mp4`

Then update `docs/index.html`:

```html
<!-- replace the video-placeholder div with: -->
<video src="demo.mp4" poster="demo-poster.jpg"
       controls autoplay muted loop style="display:block; width:100%; height:100%; object-fit:cover;"></video>
```

And delete the `<div id="videoPlaceholder">` block entirely.
