"""Clean netflix_titles.csv and load it into MongoDB.

Usage:  python import_data.py [--csv data/netflix_titles.csv]

This DROPS and recreates the `titles` and `ratings` collections of the configured database.
"""
import argparse
import sys

import pandas as pd

from cleaning import RATING_DOCS, clean_dataframe

TITLE_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["show_id", "type", "title", "release_year"],
    "properties": {
        "show_id": {"bsonType": "string"},
        "type": {"enum": ["Movie", "TV Show"]},
        "title": {"bsonType": "string", "minLength": 1},
        "release_year": {"bsonType": "int", "minimum": 1900, "maximum": 2100},
        "genres": {"bsonType": "array", "items": {"bsonType": "string"}},
        "cast": {"bsonType": "array", "items": {"bsonType": "string"}},
        "countries": {"bsonType": "array", "items": {"bsonType": "string"}},
    },
}}


def create_indexes(titles):
    titles.create_index("show_id", unique=True)
    titles.create_index([("title", "text"), ("description", "text")], name="title_text")
    titles.create_index("genres")           # multikey index (array field)
    titles.create_index("release_year")
    titles.create_index("type")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default="data/netflix_titles.csv")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.csv, dtype=str, keep_default_na=False)
    except FileNotFoundError:
        sys.exit(f"CSV not found: {args.csv}\nDownload netflix_titles.csv from Kaggle (see README) "
                 "or try data/sample_netflix_titles.csv.")

    docs, report = clean_dataframe(df)

    from pymongo.errors import PyMongoError
    from db import DB_NAME, MONGO_URI, get_db
    try:
        db = get_db()
        db.drop_collection("titles")
        db.drop_collection("ratings")
        db.create_collection("titles", validator=TITLE_VALIDATOR)
        titles = db["titles"]
        for i in range(0, len(docs), 1000):
            titles.insert_many(docs[i:i + 1000])
        create_indexes(titles)
        db["ratings"].insert_many([dict(r) for r in RATING_DOCS])
        db["ratings"].create_index("code", unique=True)
        stored = titles.count_documents({})
    except PyMongoError as exc:
        sys.exit(f"MongoDB error ({MONGO_URI}): {exc}\nIs MongoDB running?")

    print(f"Imported into database '{DB_NAME}'\n")
    for key, value in report.items():
        print(f"  {key:28s} {value}")
    print(f"  {'documents in titles':28s} {stored}")
    print(f"  {'documents in ratings':28s} {len(RATING_DOCS)}")


if __name__ == "__main__":
    main()
