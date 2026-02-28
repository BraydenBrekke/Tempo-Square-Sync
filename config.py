import yaml
from pathlib import Path


def load_config(path: str | None = None) -> dict:
    resolved = Path(path) if path is not None else Path(__file__).parent / "config.yaml"

    if not resolved.exists():
        raise FileNotFoundError(
            f"Config file not found at {resolved}. "
            "Copy config.example.yaml to config.yaml and fill in your values."
        )

    with open(resolved) as f:
        return yaml.safe_load(f)
