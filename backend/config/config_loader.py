"""
config/config_loader.py
-----------------------
Access to the metric and dimension configuration.

metrics_config.json is the single source of truth for metric display
metadata and aggregation weights. Metric names are never hardcoded in
the frontend, so adding an entry to that file is what surfaces a metric
in the user interface.
"""

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
    

def load_dimensions_config():
    """
    Load dimensions from the JSON configuration file

    Returns
    -------
    dict
        Dictionary mapping metric IDs to configuration objects.
    """
    with open(CONFIG_PATH) as f:
        return json.load(f)["dimensions"]