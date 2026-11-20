"""Pure data-cleaning helpers (no database access) shared by the importer and the web app."""
import re
from datetime import datetime

TYPES = ["Movie", "TV Show"]

# Reference data for the `ratings` collection (used with $lookup).
RATING_DOCS = [
    {"code": "TV-MA", "description": "Mature audiences only", "audience_group": "Adults"},
    {"code": "R", "description": "Restricted, under 17 needs a guardian", "audience_group": "Adults"},
    {"code": "NC-17", "description": "No one 17 and under admitted", "audience_group": "Adults"},
    {"code": "TV-14", "description": "Parents strongly cautioned", "audience_group": "Teens"},
    {"code": "PG-13", "description": "Parents strongly cautioned for under 13", "audience_group": "Teens"},
    {"code": "TV-PG", "description": "Parental guidance suggested", "audience_group": "Older Kids"},
    {"code": "PG", "description": "Parental guidance suggested", "audience_group": "Older Kids"},
    {"code": "TV-Y7", "description": "Directed to children 7 and older", "audience_group": "Older Kids"},
    {"code": "TV-Y7-FV", "description": "Children 7 and older, fantasy violence", "audience_group": "Older Kids"},
    {"code": "TV-G", "description": "General audiences", "audience_group": "Family"},
    {"code": "G", "description": "General audiences", "audience_group": "Family"},
    {"code": "TV-Y", "description": "Suitable for all children", "audience_group": "Kids"},
    {"code": "NR", "description": "Not rated", "audience_group": "Unrated"},
    {"code": "UR", "description": "Unrated", "audience_group": "Unrated"},
]

REQUIRED_COLUMNS = {
    "show_id", "type", "title", "director", "cast", "country",
    "date_added", "release_year", "rating", "duration", "listed_in", "description",
}

DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d")


def split_list(value):
    """'A, B,, A' -> ['A', 'B'] (trimmed, empty items dropped, duplicates removed, order kept)."""
    parts = [p.strip() for p in str(value or "").split(",")]
    return list(dict.fromkeys(p for p in parts if p))


def parse_date(value):
    value = str(value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_duration(value):
    """'112 min' -> (112, 'min'); '2 Seasons' -> (2, 'Season(s)'); '' -> (None, '')."""
    m = re.match(r"^\s*(\d+)\s*([A-Za-z]+)", str(value or ""))
    if not m:
        return None, ""
    unit = "min" if m.group(2).lower().startswith("min") else "Season(s)"
    return int(m.group(1)), unit


def clean_dataframe(df):
    """Turn the raw Netflix CSV (as a DataFrame) into MongoDB documents.

    Returns (documents, report). `report` holds the counts used in the project report.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")

    report = {k: 0 for k in (
        "rows_read", "duplicates_removed", "skipped_invalid", "rating_moved_from_duration",
        "missing_director", "missing_cast", "missing_country", "missing_date_added",
        "missing_rating", "kept",
    )}
    seen, docs = set(), []

    for row in df.fillna("").astype(str).to_dict("records"):
        row = {k: v.strip() for k, v in row.items()}
        report["rows_read"] += 1

        show_id = row["show_id"]
        if not show_id:
            report["skipped_invalid"] += 1
            continue
        if show_id in seen:
            report["duplicates_removed"] += 1
            continue

        # A few source rows hold the duration ("74 min") in the rating column.
        rating, duration = row["rating"], row["duration"]
        if re.fullmatch(r"\d+\s*min", rating, flags=re.I) and not duration:
            rating, duration = "", rating
            report["rating_moved_from_duration"] += 1

        year = int(row["release_year"]) if row["release_year"].isdigit() else None
        if row["type"] not in TYPES or not row["title"] or year is None:
            report["skipped_invalid"] += 1
            continue
        seen.add(show_id)

        directors = split_list(row["director"])
        cast = split_list(row["cast"])
        countries = split_list(row["country"])
        date_added = parse_date(row["date_added"])
        value, unit = parse_duration(duration)

        report["missing_director"] += not directors
        report["missing_cast"] += not cast
        report["missing_country"] += not countries
        report["missing_date_added"] += date_added is None
        report["missing_rating"] += not rating

        docs.append({
            "show_id": show_id,
            "type": row["type"],
            "title": row["title"],
            "directors": directors,
            "cast": cast,
            "countries": countries,
            "date_added": date_added,
            "release_year": year,
            "rating": rating or "NR",
            "duration_value": value,
            "duration_unit": unit,
            "genres": split_list(row["listed_in"]),
            "description": row["description"],
        })

    report["kept"] = len(docs)
    return docs, report
