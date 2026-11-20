"""The five analyses from the project report. Each function takes a pymongo Database."""
from pymongo.errors import OperationFailure


def type_counts(db):
    """Analysis 2a: movies vs TV shows."""
    return list(db.titles.aggregate([
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))


def titles_per_year(db, limit=10):
    """Analysis 2b: titles per release year (latest years first)."""
    rows = list(db.titles.aggregate([
        {"$group": {"_id": "$release_year", "count": {"$sum": 1}}},
        {"$sort": {"_id": -1}},
        {"$limit": limit},
    ]))
    return sorted(rows, key=lambda r: r["_id"])


def duration_stats(db):
    """Analysis 2c: movie duration statistics (minutes)."""
    rows = list(db.titles.aggregate([
        {"$match": {"type": "Movie", "duration_value": {"$ne": None}}},
        {"$group": {"_id": None,
                    "avg_minutes": {"$avg": "$duration_value"},
                    "shortest": {"$min": "$duration_value"},
                    "longest": {"$max": "$duration_value"},
                    "movies": {"$sum": 1}}},
    ]))
    return rows[0] if rows else {"avg_minutes": 0, "shortest": 0, "longest": 0, "movies": 0}


def _top(db, field, limit):
    return list(db.titles.aggregate([
        {"$unwind": f"${field}"},
        {"$group": {"_id": f"${field}", "titles": {"$sum": 1}}},
        {"$sort": {"titles": -1, "_id": 1}},
        {"$limit": limit},
    ]))


def top_genres(db, limit=10):
    """Analysis 3a: most common genres ($unwind on an array field)."""
    return _top(db, "genres", limit)


def top_countries(db, limit=10):
    """Analysis 3b: countries with the most titles."""
    return _top(db, "countries", limit)


def audience_groups(db):
    """Analysis 4: titles per audience group, joining `ratings` with $lookup."""
    return list(db.titles.aggregate([
        {"$lookup": {"from": "ratings", "localField": "rating",
                     "foreignField": "code", "as": "rating_info"}},
        {"$unwind": "$rating_info"},
        {"$group": {"_id": "$rating_info.audience_group", "titles": {"$sum": 1}}},
        {"$sort": {"titles": -1}},
    ]))


def index_performance(db, year=2018):
    """Analysis 5: explain('executionStats') for a release_year query without and with an index.

    Drops and recreates the release_year index, so it ends with the index in place.
    """
    cmd = {"explain": {"find": "titles", "filter": {"release_year": year}},
           "verbosity": "executionStats"}

    def stats():
        plan = db.command(cmd)
        ex = plan["executionStats"]
        stage = plan["queryPlanner"]["winningPlan"]
        while "inputStage" in stage:       # find the leaf stage: COLLSCAN or IXSCAN
            stage = stage["inputStage"]
        return {"stage": stage["stage"], "docs_examined": ex["totalDocsExamined"],
                "returned": ex["nReturned"], "millis": ex["executionTimeMillis"]}

    try:
        db.titles.drop_index("release_year_1")
    except OperationFailure:
        pass                                # index did not exist
    before = stats()
    db.titles.create_index("release_year")
    after = stats()
    return {"year": year, "before": before, "after": after}
