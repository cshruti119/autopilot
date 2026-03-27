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