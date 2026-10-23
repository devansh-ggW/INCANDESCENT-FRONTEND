# INCANDESCENT — Windows downloads

Download the actual Windows application from **Releases**, not from GitHub's **Code → Download ZIP** source archive.

## Downloads

- **[Download INCANDESCENT Setup](https://github.com/devansh-ggW/INCANDESCENT-FRONTEND/releases/download/v1.0.0/INCANDESCENT-Setup.exe)** — recommended; installs the app and provides model setup.
- [Download the standalone INCANDESCENT app](https://github.com/devansh-ggW/INCANDESCENT-FRONTEND/releases/download/v1.0.0/INCANDESCENT.exe)
- [Release page and all files](https://github.com/devansh-ggW/INCANDESCENT-FRONTEND/releases/tag/v1.0.0)

The executable files are distributed as release assets. They are intentionally not stored as regular source files in this repository because they exceed GitHub's 100 MiB ordinary-file limit.

## Install

1. Download **INCANDESCENT-Setup.exe** from the Releases page above.
2. Run the downloaded installer.
3. INCANDESCENT uses your existing Ollama installation; this installer does not install Ollama itself.
4. The model setup can download `qwen3.5:2b` through Ollama if it is not already present.

The initial installer targets 64-bit Windows 10 and later. Windows ARM64 is best-effort through x64 emulation. Windows 7/8/8.1 and 32-bit Windows are not supported.

## Important

Do not run a 134-byte `.exe` file from an LFS pointer or repository archive. Use the release links above to download the actual executable.
