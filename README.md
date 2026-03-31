# Hello Python

A simple Hello World Python project using the uv package manager.

## About

This project demonstrates setting up a basic Python application using uv, a fast Python package manager and resolver.

## Features

- Simple Hello World application
- Configured with uv package manager
- Development dependencies included (pytest, black, flake8)
- Standard Python project structure

## Requirements

- Python 3.8 or higher
- uv package manager

## Installation

1. Clone this repository
2. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Sync the project dependencies:
   ```bash
   uv sync
   ```

## Usage

Run the application:
```bash
uv run python -m hello_python.main
```

Or use the console script:
```bash
uv run hello
```

## Development

Install development dependencies:
```bash
uv sync --dev
```

Run Checkpoint UI:
```bash
uvicorn checkpoints.ui.server:app --port 8080 --reload
```

Run tests:
```bash
uv run pytest
```

Format code:
```bash
uv run black .
```

Lint code:
```bash
uv run flake8
```

## Project Structure

```
.
├── README.md
├── pyproject.toml
├── hello_python/
│   ├── __init__.py
│   └── main.py
└── .venv/
```

## License

MIT License
----------

# 1. Start infra
cd infra && docker-compose up -d

# 2. Activate env
source .venv/bin/activate

# 3. Create your tic-tac-toe repo on GitHub, clone it locally
git clone https://github.com/your-username/tic-tac-toe
# Set TARGET_REPO_PATH in .env to this path

# 4. Create a Jira story titled "Build Tic-Tac-Toe game"
# Note the story ID e.g. TIC-1

# 5. In one terminal — run checkpoint UI
uvicorn checkpoints.ui.server:app --port 8080

# 6. In another terminal — run the pipeline
python main.py
# Pipeline pauses at spec → open localhost:8080/checkpoint/TIC-1
# Approve spec → pipeline resumes automatically