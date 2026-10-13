def assign_ranks(rows):
    rows = list(rows)
    rank, previous = 0, None
    for position, row in enumerate(rows, start=1):
        if row.total_points != previous:
            rank, previous = position, row.total_points
        row.rank = rank
    return rows