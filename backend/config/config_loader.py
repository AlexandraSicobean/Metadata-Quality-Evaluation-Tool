import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "metrics_config.json"

def load_metrics_config():
    """
    Load metric configurations from the JSON configuration file
    
    The config file contains the name, description, dimension,
    subdimension, weight, and optionally shape files locations

    Returns
    -------
    dict
        Dictionary mapping metric IDs to configuration objects.
    """
    with open(CONFIG_PATH) as f:
        return json.load(f)["metrics"]