# Mini Maya Studio

A small Maya-style 3D layout and animation studio that runs in the browser, served from your Mac by a tiny Python server (standard library only, nothing to pip install).

## Install or update

Every release is a uniquely named zip, `minimaya-v<version>-<build>.zip`. From the folder holding the zip:

```
unzip -q minimaya-v*-*.zip -d /tmp/mm-install && bash /tmp/mm-install/minimaya/install.sh
```

The installer copies the app to `~/Sites/minimaya`, backs up the previous build into `releases/` (last five kept), installs a launchd agent (`com.manish.minimaya`) so the server starts at login and restarts if it stops, waits for the health check, commits the build to a local git repo, pushes to a public GitHub repo named `minimaya` when the `gh` CLI is logged in, and opens the app.

Your scenes in `~/Sites/minimaya/data/scenes` are never touched by an update.

| Setting | Default | Change with |
|---|---|---|
| Port | 48713 | `MINIMAYA_PORT=50123 bash install.sh` |
| Bind address | 127.0.0.1 | `MINIMAYA_HOST=0.0.0.0` (LAN access) |
| Install folder | ~/Sites/minimaya | `MINIMAYA_DEST=...` |
| GitHub push | on when gh is logged in | `MINIMAYA_NO_PUSH=1` |
| Open browser | on | `MINIMAYA_NO_OPEN=1` |

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
| GET | /api/health | app, version |
| GET | /api/scenes | list saved scenes |
| GET/PUT/DELETE | /api/scenes/<name> | read, save, delete a scene (JSON) |

## Files

`index.html` is the whole app. `vendor/` holds three.js r128 and its controls and exporters, so the studio works offline. `server.py` serves the app and the API.
