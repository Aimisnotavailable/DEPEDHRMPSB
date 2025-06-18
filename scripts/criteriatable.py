class CriteriaTable:
    """
    Calculates delta score by subtracting baseline from a raw score,
    ensuring a minimum of zero.
    """
    def get_score(self, score: int, baseline: int) -> int:
        return max(score - baseline, 0)
