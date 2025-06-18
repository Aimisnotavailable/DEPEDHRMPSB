class IncrementsTable:
    """
    Maps a delta score into a transmuted bracket using a JSON table:
      { "1": {"MAX": 2}, "2": {"MAX": 4}, … }
    """
    def get_score(self, un_transmutated_score: int, table: dict[str, dict[str, int]]) -> int:
        if not table:
            raise ValueError("No increments table provided.")
        sorted_keys = sorted(table.keys(), key=lambda x: int(x))
        for bracket in sorted_keys:
            if un_transmutated_score <= table[bracket]["MAX"]:
                return int(bracket)
        return int(sorted_keys[-1])
