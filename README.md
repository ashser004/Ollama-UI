# Local AI(UI)

A fully offline, portable AI workspace powered by Ollama. Built with PySide6.

> **Everything stays in one folder.** Delete it to remove everything.

## Features

- 🧠 **Fully Offline** — No cloud, no API keys, complete privacy
- 📦 **Portable** — Runs from any folder, even a USB drive
- 🔍 **Model Discovery** — Browse & install 25+ AI models under 10GB
- 💬 **Chat Interface** — Streaming responses with conversation history
- 🔀 **Agentic Mode** — Switch models mid-conversation with context management
- 📷 **Vision Support** — Upload images to compatible models
- 📊 **System Monitor** — Real-time CPU, RAM, and disk tracking
- 🎨 **Premium Dark UI** — Gorgeous violet-accented dark theme

## Quick Start

### 1. Create virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python main.py
```

### 4. First launch
1. Choose a storage directory (where AIUI folder will be created)
2. Click "Install Ollama" — downloaded and set up automatically
3. Browse and install models
4. Start chatting!

## Project Structure

```
LOCALAIUI/
├── main.py                 # Entry point
├── models.json             # AI model catalog
├── requirements.txt        # Python dependencies
├── app/
│   ├── config.py           # Configuration & paths
│   ├── database.py         # SQLite chat storage
│   ├── theme.py            # Dark theme & styling
│   ├── ollama/
│   │   ├── manager.py      # Ollama binary lifecycle
│   │   ├── api.py          # REST API wrapper
│   │   └── model_catalog.py # Model catalog management
│   ├── services/
│   │   ├── system_monitor.py   # CPU/RAM/Disk monitoring
│   │   └── download_manager.py # Resumable downloads
│   ├── widgets/            # Reusable UI components
│   └── pages/              # Application pages
└── assets/icons/           # SVG icons (future)
```

## Maintaining `models.json`

The `models.json` file is the catalog of available models. To add new models:

1. Open `models.json`
2. Add a new entry to the `models` array:
```json
{
  "name": "Display Name",
  "tag": "ollama-tag-name",
  "size_gb": 4.5,
  "min_ram_gb": 8,
  "description": "Short description of the model.",
  "capabilities": ["chat", "coding", "reasoning"],
  "supports_images": false,
  "supports_files": false,
  "context_window": 8192
}
```
3. Increment the `version` field
4. Update `last_updated` date

### Fields Reference
| Field | Description |
|-------|-------------|
| `name` | Display name shown in the UI |
| `tag` | Exact Ollama tag for `ollama pull <tag>` |
| `size_gb` | Download size in GB |
| `min_ram_gb` | Minimum RAM needed to run the model |
| `description` | 1-2 line description |
| `capabilities` | Array of: `chat`, `coding`, `reasoning`, `vision`, `math`, `embedding` |
| `supports_images` | `true` if model accepts image inputs |
| `supports_files` | `true` if model accepts file uploads |
| `context_window` | Token context window size |

### Future: GitHub-hosted catalog
Later, push `models.json` to your GitHub repo. Update `config.py` to fetch from:
```
https://raw.githubusercontent.com/ashser004/LOCALAIUI/main/models.json
```

## Developer

**Ashmith Babu P S** — [github.com/ashser004](https://github.com/ashser004)

## License

MIT
