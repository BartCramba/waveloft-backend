from datetime import datetime, timedelta, timezone

MIN_EF        = 1.3      # lower bound for easiness factor
MAX_INTERVAL  = 30       # never push a card further than 30 d

def apply_sm2(ease: float, reps: int, interval: int, grade: int):
    """Return new_ease, new_reps, new_interval_days (float)."""
    new_ease = ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    if new_ease < MIN_EF:
        new_ease = MIN_EF

    if grade < 3:
        new_reps = 0
        new_interval = 0.007        # 10 minutes
    else:
        new_reps = reps + 1
        if new_reps == 1:
            new_interval = 1
        elif new_reps == 2:
            new_interval = 6
        else:
            new_interval = round(interval * new_ease)

    if new_interval > MAX_INTERVAL:
        new_interval = MAX_INTERVAL

    return new_ease, new_reps, new_interval


def next_review_at(interval_days: float) -> str:
    return (datetime.now(timezone.utc) +
            timedelta(days=interval_days)).isoformat()
