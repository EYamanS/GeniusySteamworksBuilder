# GENIUSY'S Steamworks Builder

Automation tool for uploading game builds to Steam. It saves multiple build
profiles, generates VDF files automatically, and handles uploading with
`steamcmd` in a single click.

A desktop application written in Python + [pywebview](https://pywebview.flowrl.com/).
Runs natively on **Windows and macOS**.

<img width="1157" height="423" alt="image" src="https://github.com/user-attachments/assets/317909b2-b9c4-4a3e-a097-ec6ed6382909" />

## Quickstart

1. **Get the app**
   - **macOS (Apple Silicon):** download the `.zip` from [Releases](../../releases),
     unzip, and move `GENIUS Steamworks Builder.app` wherever you like. The app is
     not notarized, so on first launch either right-click it → **Open** → **Open**,
     or clear the quarantine flag once:
     `xattr -dr com.apple.quarantine "GENIUS Steamworks Builder.app"`
   - **Windows:** download the `.exe` from [Releases](../../releases), or build it
     yourself with `build_exe.bat`.
   - Or run straight from source — see [Running](#running).
2. **Get the Steamworks SDK** from the
   [partner site](https://partner.steamgames.com/downloads/list) and unzip it
   somewhere permanent. The app only needs its `tools/ContentBuilder` folder.
3. Launch the app → **Settings** opens automatically → point it at
   `tools/ContentBuilder`, enter your Steam username and password → **Save**.
4. **+ New Game** → App ID + the build folder you want to upload →
   **BUILD & UPLOAD**. Enter the Steam Guard code when asked — later builds
   reuse the cached session.

## Requirements

### Windows

- **Windows 10 (version 1809 / October 2018 update) or Windows 11.**
  - Windows 10 1809+ provides ConPTY, which lets the live build console stream
    line by line and makes the Steam Guard prompt work reliably. On older
    Windows the app falls back to a plain pipe (no crash, just less polished
    output).
  - The Windows 11 rounded window corners are cosmetic; on Windows 10 the window
    simply has square corners.
- **[WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).**
  pywebview renders the UI with the Edge WebView2 engine. It is pre-installed on
  Windows 11 and on up-to-date Windows 10; on a stripped-down Windows 10 you may
  need to install the "Evergreen" runtime once.
- **.NET**: provided by the built-in .NET Framework on Windows (used by
  `pythonnet`); no separate install is normally needed.
- **Python 3.x**: only for developer mode (`run_dev.bat`). The built `.exe`
  bundles its own Python and does not require it.
- Passwords are stored in the **Windows Credential Manager**.

### macOS

- **macOS 11 (Big Sur) or newer.** The UI renders with the system WKWebView —
  nothing extra to install. The window uses the native frame (traffic lights,
  native resize) with a transparent titlebar.
- The live build console runs `steamcmd` inside a real **pseudo-terminal**
  (the POSIX equivalent of ConPTY), so output streams line by line and the
  Steam Guard prompt works exactly like on Windows.
- **Apple Silicon (M1/M2/M3/M4):** Valve ships `steamcmd` for macOS as an
  Intel (x86_64) binary, so it runs through **Rosetta 2**. If you have never
  installed it, run once: `softwareupdate --install-rosetta --agree-to-license`.
- The app uses the SDK's `builder_osx/steamcmd.sh` automatically (and restores
  its exec bit if the zip lost it), and passwords are stored in the
  **macOS Keychain**.
- **Python 3.x**: only for developer mode (`./run_dev.sh`). The built `.app`
  bundles its own Python and does not require it.

## The Steamworks SDK is NOT included!

This repository contains **only the builder tool**. Valve's Steamworks SDK
(including `steamcmd.exe`, ContentBuilder, etc.) is **not included** because it
is copyrighted and redistribution is not permitted. To use the tool you must
download the SDK yourself from the
[Steamworks partner site](https://partner.steamgames.com/) and point the app to
your **ContentBuilder** folder.

## Running

**Dependencies (both platforms):**
```
pip install -r requirements.txt
```

**Developer mode (with Python):**
```
run_dev.bat        # Windows
./run_dev.sh       # macOS
```

**Building a standalone app:**
```
build_exe.bat      # Windows  ->  dist\GENIUS Steamworks Builder.exe
./build_app.sh     # macOS    ->  dist/GENIUS Steamworks Builder.app
```

**Automated releases:** pushing a tag like `v1.2.0` runs a GitHub Actions
workflow that builds the Windows `.exe` and the macOS `.app` and attaches both
to a new GitHub release automatically.

## First-time setup

1. Open the app → **Settings** opens automatically.
2. **ContentBuilder folder**: the SDK's `tools/ContentBuilder` folder (the one
   that contains `builder\steamcmd.exe` on Windows / `builder_osx/steamcmd.sh`
   on macOS). It is usually detected automatically.
3. Enter your **Steam username** and **password**. The password is stored
   encrypted in the Windows Credential Manager / macOS Keychain. It is never
   written to disk in plain text.
4. **Save**.
5. Use the **Import** button to automatically load your existing games from the
   `scripts/` folder as profiles.

## Usage

- Select a game from the game list, or create one with **+ New Game**.
- Each profile has: an **App ID**, a description, a beta branch (setlive), and one
  or more **depots** (Depot ID + content folder + exclusions).
- **BUILD & UPLOAD** → VDFs are generated, `steamcmd` runs, and the live console streams.
- **Preview Build** → tests without uploading to Steam.

<img width="705" height="425" alt="image" src="https://github.com/user-attachments/assets/5bdcff66-4ea8-4552-88ad-6092913c53b1" />

## Steam Guard (2FA)

When a Steam Guard code is requested during a build, the app opens a window and
asks for the code. After a successful login, `steamcmd` caches the session
(a sentry file under the builder folder's `config/`), so in the ideal case it
will not ask again on later builds.

### Why it may keep asking every build

Steam only allows one active session per account at a time. If you are signed
in to the **same account** in the desktop Steam client, logging in through
`steamcmd` kicks that session (and vice versa). Every time the cached session is
kicked, the next build has to log in from scratch, which triggers Steam Guard
**again**. So on a machine where you also use the desktop Steam client with the
same account, you may be asked for a code on almost every build. This is the
default behavior of Steam itself, not a bug in this tool.

### Recommended fix: a dedicated build account

The reliable way to stop both the repeated Steam Guard prompts and the desktop
client being logged out is to use a **separate Steam account just for uploading**:

1. Create a new Steam account (e.g. `yourstudio_builder`).
2. In the [Steamworks](https://partner.steamgames.com/) partner site, under
   **Users & Permissions**, grant that account publish/build access to your app.
3. Enter this build account in the app's **Settings** instead of your personal one.
4. Keep your personal account signed in to the desktop Steam client.

Because the build account is never used by the desktop client, its `steamcmd`
session is not kicked: you enter the Steam Guard code **once**, and later builds
reuse the cached session. Leaving the build account on **email-based** Steam
Guard (rather than the mobile authenticator) tends to keep the cached token more
stable for automated uploads.

If you must use the same account for everything, sign **out** of the desktop
Steam client before building to reduce how often the session is invalidated.

## How it works

On each build the following files are (re)generated inside `tools/ContentBuilder/scripts/`:

- `app_<AppID>.vdf`: build definition + depot list
- `depot_<DepotID>.vdf`: content folder and file rules for each depot

Paths are always written as absolute paths from the ContentBuilder location, so
the broken-path problem in old `.vdf` files fixes itself.

The command that is then run:
```
builder\steamcmd.exe          +login <username> <password> +run_app_build <app_vdf> +quit   (Windows)
builder_osx/steamcmd.sh       +login <username> <password> +run_app_build <app_vdf> +quit   (macOS)
```

On both platforms steamcmd is attached to a pseudo-terminal (ConPTY on
Windows, a POSIX pty on macOS) so the console streams live and the Steam
Guard prompt can be answered from the app.

## License

[MIT](LICENSE). The Steamworks SDK is outside the scope of this license and belongs to Valve.
