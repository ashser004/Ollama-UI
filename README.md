# Local AI

Your fully offline, portable, and private AI workspace powered by Ollama.

Local AI provides a stunning, seamless interface to download, manage, and chat with the world's most powerful open-source AI models right on your own hardware. 
Built with a focus on **absolute privacy**, **smart memory management**, and **beautiful design**.

---

## Features

* **Fully Offline & Private** — No cloud, no API keys, and zero data leaves your device.
* **Smart Context Memory** — Dynamically manages RAM by calculating the perfect conversational budget (up to 16,384 tokens) so the AI never forgets your chat and your PC never crashes.
* **Portable Workspace** — Runs perfectly from any folder, or even a USB flash drive. Everything stays in one place.
* **Live Model Discovery** — A curated, built-in store to browse and install 30+ highly optimized AI models (Llama 3, DeepSeek, Qwen, Phi-4) that fit your PC's hardware.
* **Vision & Image Support** — Chat with images using multimodal models like Llava and Llama 3.2 Vision.
* **Seamless Model Switching** — Change AI models mid-conversation. The app automatically unloads the old model from RAM and passes your entire chat history to the new one.
* **Real-Time System Monitor** — Keep an eye on your CPU, RAM, and Disk usage directly inside the app.
* **GPU-Accelerated Image Generation** — Generate images from text prompts entirely on-device using Stable Diffusion. Automatically detects your NVIDIA GPU and downloads the CUDA-enabled engine for fast generation, or falls back to a lightweight CPU build.

---

## How It Works

Local AI is essentially a beautiful, intelligent wrapper around the powerful **Ollama** engine.

Instead of typing commands in a terminal:
1. You browse the **Discover** tab to find an AI model that fits your hardware (indicated by color-coded RAM tags).
2. You click install, and the app downloads it directly to your portable folder.
3. You start chatting. The app automatically translates your chat history into strict JSON payloads, perfectly formatting them for the AI to understand.
4. For image generation, select an image model and describe what you want — the engine handles everything offline.

This means:
* No terminal commands required.
* Professional-grade memory management (just like ChatGPT or Claude).
* Fast, native performance built on Python and PySide6.

---

## Installation

### Option 1 – Windows Installer (Recommended)

1. Go to the **Releases** section of this repository.
2. Download `LOCAL AI Setup.exe`.
3. Run the installer and follow the prompts.
4. Launch the app and choose where you want your portable AI folder to live.

---

### Option 2 – Build From Source

Requirements:
* Python 3.11+
* Git

Steps:

```bash
git clone https://github.com/ashser004/Ollama-UI.git
cd Ollama-UI
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

---

## Usage Guide

### 1. Initial Setup
On your first launch, select a storage directory. The app will automatically download and configure the Ollama engine inside this folder.

### 2. Discover Models
Navigate to the **Discover** tab. You will see a curated list of models. 
* Models are automatically filtered based on your computer's available RAM.
* Click **Install** on a model (like `gemma3:4b` or `phi4-mini`) to download it.

### 3. Start Chatting
Go to the **Chat** tab, select your downloaded model from the dropdown, and say hello!
You can attach up to 5 images if you are using a Vision-capable model.

### 4. Generate Images
Enable **Image Generation** from the home dashboard. Install an image model from **Discover**, then select it in Chat and describe the image you want.

### 5. Manage Your System
Keep an eye on the bottom status bar or the Logs page to see your real-time RAM usage and background download progress. You can also manage installed models, including image models, from the **Manage** tab.

---

## Technical Highlights

Local AI was built to solve the common issues found in other AI GUIs:
* **No "Default 4K Squeeze"**: Unlike basic CLI tools that forget conversations quickly, Local AI actively expands the context window up to 16,384 tokens depending on the model's capacity.
* **Graceful Unloading**: Switching models triggers a `keep_alive: 0` command, instantly freeing up your RAM before loading the next AI.
* **Tail-Read Logging**: The built-in log viewer is highly optimized, reading only the last 500 lines to prevent UI freezing, even during massive installation processes.
* **Hardware-Aware Image Engine**: At download time, `nvidia-smi` is queried to detect NVIDIA GPUs. GPU systems receive the CUDA-enabled binary and runtime DLLs; CPU-only systems receive a small AVX2 build.
* **Pipe-Safe Subprocess Design**: The image generation subprocess uses `communicate()` instead of `wait()`, preventing the Windows pipe buffer deadlock that causes generation to hang after loading.

---

## Contributing

Contributions are welcome! 
If you want to add new models to the catalog, you can edit the `models.json` file. Please ensure any added model has accurate `min_ram_gb` and `context_window` limits verified from the official Ollama library.

You can:
* Report bugs
* Suggest UI improvements
* Submit pull requests

---

## Developer

Developed and maintained by **Ashmith Babu P S** 
* GitHub: [ashser004](https://github.com/ashser004)
* A passion project focused on making local AI accessible, private, and beautifully designed.

---

## License

Local AI is licensed under the **MIT License**.
See the LICENSE file for full terms.

© 2026 Ashmith
