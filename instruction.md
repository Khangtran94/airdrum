# Install, run and test

See [README.md](README.md) for the current commands, lesson progression, controls,
latency behavior and troubleshooting. The README is the authoritative guide.

Quick start on Windows:

```powershell
uv sync
uv run airdrum --keyboard --lesson backbeat --bpm 60 --bars 4 --listen
uv run airdrum --keyboard --lesson backbeat --bpm 60 --bars 4
```

For iVCam, connect your phone and desktop client, run
`uv run python -m airdrum.camera`, then choose the reported camera index.
