def assign_ranks(rows):
    rows = list(rows)
    rank, previous = 0, None
    for position, row in enumerate(rows, start=1):
        if row.total_points != previous:
            rank, previous = position, row.total_points
        row.rank = rank
    return rows


def attach_predictions(user, matches):
    matches = list(matches)
    if not user.is_authenticated or not matches:
        for match in matches:
            match.my_prediction = None
        return matches
    from .models import Prediction
    saved = {p.match_id: p for p in Prediction.objects.filter(user=user, match__in=matches).select_related("points")}
    for match in matches:
        match.my_prediction = saved.get(match.id)
    return matches


def parse_score(raw, max_value):
    raw = (raw or "").strip()
    if not raw.isdigit() or int(raw) > max_value:
        raise ValueError(raw)
    return int(raw)
