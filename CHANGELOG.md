# Changelog

## 0.3.0
- Characters: little humans and animals (cat, dog, bear, bunny, fox, pig, panda) with rigs, blinking eyes, brows, talking mouths, ears, tails, hair styles, skin-tone presets and clothes
- Acting: 15 actions (Walk to and Run to with a ground pick, Wave, Talk, Jump, Dance, Cheer, Point, Think, Look around, Sit, Sad, Surprised, Angry, Play animation) with blending, expressions, dialogue lines and facing direction
- Story panel (T): per-character clip tracks, camera shots, audio track with waveform; drag, resize, delete
- Cameras: camera from view, lens, aim at a character, shot cuts; Film view (V) with format gate and subtitles
- Sets: ten props, gradient sky, ground, sun and fill light with Day, Golden hour and Night presets, image-based lighting
- Media: import rigged GLB models with animations; audio track synced to playback
- Render: Landscape, Vertical 9:16, Square and 720p presets, supersampling, burned-in subtitles; MP4 movie with sound encoded by ffmpeg on the studio Mac
- Server: asset storage, frame upload and ffmpeg encoding, media with byte ranges; installer adds ffmpeg through Homebrew and gives launchd a Homebrew PATH
- Shelf is now tabbed: Create, Characters, Acting, Set, Camera, Media
- First run of 0.3 opens a demo movie; Undo returns to your previous scene

## 0.2.0
- Studio server (Python, stdlib only) with a scene library: Save to studio (Ctrl S), Save as, Open, Delete
- Graph Editor: per-channel curves, drag keys in value or time, zoom and pan, spline / linear / stepped curves, exact key fields
- Multi-select (Shift-click in viewport and Outliner), moving several objects at once
- Hierarchy: Parent (P), Unparent (Shift P), Group (Ctrl G), drag-and-drop parenting in the Outliner, duplicate and delete whole branches
- Render: clean still at any size (PNG) and playblast of the frame range (WebM or MP4)
- Export: animated GLB (baked per frame) and OBJ; scene JSON download
- Seed scene shows a spinning group with children
- Offline: three.js vendored; install script with launchd agent, backups, git commit and GitHub push

## 0.1.0
- Viewport, shelf, toolbox, Outliner, Attribute Editor, time slider, keys, undo, autosave
