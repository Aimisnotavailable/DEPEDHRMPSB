import json
from scripts.path import TABLE_PATH, TRANSMUTATION_PATH

PATHS = {
    "table": TABLE_PATH,
    "increments": TRANSMUTATION_PATH
}

class TableHandler:
    """
    Loads JSON files from either:
      - <cwd>/tables/<stype>.json
      - <cwd>/increments_transmutation/<stype>.json
    """
    def parse_table(self, t_type: str = "table", s_type: str = "education") -> dict:
        path = f"{PATHS[t_type]}/{s_type}.json"
        try:
            with open(path, encoding="utf-8") as fp:
                return json.load(fp)
        except FileNotFoundError:
            # missing file → empty dict
            return {}
