# Mini Maya Studio

A small Maya-style 3D layout and animation studio that runs in the browser, served from your Mac by a tiny Python server (standard library only, nothing to pip install). Since 0.3 it makes short 3D movies with little human and animal characters, finished as MP4 with sound.

## Making a movie

1. **Characters tab**: add a human, cat, dog, bear, bunny, fox, pig, panda, tiger, lion or raccoon. The Attribute Editor changes species, skin or fur color, fur length, hair, clothes, size, and the character's voice, pitch and speed.
2. **Set tab**: dress the scene with props, and open Environment for sky, ground and sun (Day, Golden hour, Night).
3. **Acting tab**: select a character, click an action. It lands at the current frame and the playhead jumps to its end, so the next click follows on. Walk to and Run to ask you to click the ground for the destination.
4. **Story panel (T)**: every clip on one timeline. Drag to move, drag the right edge to resize, click a clip to set its facial expression, dialogue line, talking mouth and facing direction. Typing a Line on a Talk clip speaks it in the character's voice (on the local studio) and the mouth follows the sound; the line also shows as a subtitle. Voice all lines re-speaks anything that changed. Delete removes a clip.
5. **Camera tab**: Camera from view places a camera where you are looking; Add shot cuts to the selected camera at the current frame. Film view (V) shows the movie through the shots, framed to the output format.
6. **Media tab**: add a music or voice track, or import a rigged GLB character (for example from Mixamo) and play its animations with Play animation, Walk to and Run to.
7. **Render**: pick Landscape 1920×1080, Vertical 1080×1920 (Reels, TikTok, Shorts) or Square, then Render movie (MP4). Frames render one by one, ffmpeg on the Mac encodes H.264 with AAC audio, and the file lands in `data/renders`.

File, Open demo movie loads a 9-second example with three characters and two cameras.

Voices: the installer puts Piper (offline neural text-to-speech) in `.venv` and downloads the voices named in `voices.txt` into `data/voices`; lines can be full Piper voice names or language codes such as `ne_NP`. On a Mac the system voices appear too. Generated lines are cached in `data/assets`.

Limits: characters are stylized rigs with rigid limbs (no soft skin deformation); Piper's Hindi and Nepali voices are natural but not studio-actor quality; fur is heavy for weak GPUs (use Display, Fur: light); GLB export carries keyframe animation but not story acting; WebM playblasts have no sound (the MP4 path does).

## Install or update

Every release is a uniquely named zip, `minimaya-v<version>-<build>.zip`. From the folder holding the zip:

```
unzip -q minimaya-v*-*.zip -d /tmp/mm-install && bash /tmp/mm-install/minimaya/install.sh
```

The installer copies the app to `~/Sites/minimaya`, backs up the previous build into `releases/` (last five kept), installs a launchd agent (`com.manish.minimaya`) so the server starts at login and restarts if it stops, waits for the health check, commits the build to a local git repo, pushes to a public GitHub repo named `minimaya` when the `gh` CLI is logged in, and opens the app.

Your scenes, media and movies in `~/Sites/minimaya/data` are never touched by an update. If Homebrew is present and ffmpeg is missing, the installer runs `brew install ffmpeg` so MP4 export works.

| Setting | Default | Change with |
|---|---|---|
| Port | 48713 | `MINIMAYA_PORT=50123 bash install.sh` |
| Bind address | 127.0.0.1 | `MINIMAYA_HOST=0.0.0.0` (LAN access) |
| Install folder | ~/Sites/minimaya | `MINIMAYA_DEST=...` |
| GitHub push | on when gh is logged in | `MINIMAYA_NO_PUSH=1` |
| Open browser | on | `MINIMAYA_NO_OPEN=1` |
| ffmpeg via Homebrew | on when missing | `MINIMAYA_NO_FFMPEG=1` |
| Offline voices (Piper) | on | `MINIMAYA_NO_TTS=1` |

## Everyday control

```
~/Sites/minimaya/ctl.sh status
~/Sites/minimaya/ctl.sh restart
~/Sites/minimaya/ctl.sh logs
~/Sites/minimaya/ctl.sh stop
~/Sites/minimaya/run.sh
~/Sites/minimaya/uninstall.sh
```

`run.sh` runs the server in the foreground (stop the agent first so the port is free).

## Putting it on the internet (optional)

The server binds to localhost, which is what cloudflared needs. Add an ingress rule to the tunnel config that serves your other hostnames, for example `hostname: minimaya.example.com` with `service: http://localhost:48713`, create the CNAME, and restart cloudflared. There is no login on the app, so anyone with the URL can save and delete studio scenes; put Cloudflare Access in front of it if that matters.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | app, version, whether ffmpeg is available |
| GET | /api/scenes | list saved scenes |
| GET/PUT/DELETE | /api/scenes/<name> | read, save, delete a scene (JSON) |
| GET | /api/assets | list uploaded models and audio |
| PUT | /api/assets/<file> | upload a glb, mp3, wav, m4a, aac, ogg, png or jpg (300 MB max) |
| PUT | /api/render/<job>/<n> | upload frame n of a movie render (PNG) |
| POST | /api/render/<job>/finish | encode the frames (and audio) to MP4 with ffmpeg |
| DELETE | /api/render/<job> | discard a cancelled render |
| GET | /api/renders | list finished movies |
| GET | /api/tts/voices | voices from Piper, macOS and espeak-ng |
| POST | /api/tts | speak {text, voice, pitch, rate} into a cached WAV asset |
| GET | /media/assets/<file>, /media/renders/<file> | media, with byte ranges for video seeking |

## Files

`index.html` is the whole app. `vendor/` holds three.js r128 and its controls, exporters, GLTF loader and room environment, so the studio works offline. `server.py` serves the app and the API.
