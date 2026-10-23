# INCANDESCENT

A local desktop AI workspace powered by Ollama, with conversational chat, code help, image analysis, saved chats and configurable assistant profiles.

## Windows download

**[Download the INCANDESCENT v1.1.1 installer](https://github.com/devansh-ggW/INCANDESCENT-FRONTEND/releases/download/v1.1.1/INCANDESCENT-Setup.exe)**

[Release page and files](https://github.com/devansh-ggW/INCANDESCENT-FRONTEND/releases/tag/v1.1.1)

The installer uses your existing Ollama installation; it does not install Ollama. When Ollama is responding, setup automatically downloads `qwen3.5:2b` if missing. The app also attempts to start your already-installed local Ollama service if it is not listening. The model download requires internet access and several gigabytes of storage.

## Custom AIs

After creating and saving an AI profile, choose either:

- **Add to Ollama** to create a local model named from the AI's name, using `qwen3.5:2b`.
- **Download portable files** to export a ZIP containing an editable `Modelfile`, profile metadata, and setup instructions. The ZIP does not contain the multi-gigabyte model weights; another PC needs Ollama and `qwen3.5:2b`.

Custom profiles configure instructions and context on top of a base model; this is not model-weight fine-tuning.

## Build from source

Use Python 3.11 and the dependencies in `requirements-desktop.txt`, then run `python desktop_app.py`. GitHub Actions builds the Windows app and installer.
