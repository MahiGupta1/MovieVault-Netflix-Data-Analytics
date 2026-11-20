import math
import os
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from pymongo.errors import PyMongoError, WriteError

import analysis
from cleaning import TYPES, parse_duration, split_list
from db import get_db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

PER_PAGE = 24
SORTS = {
    "newest": [("release_year", -1), ("title", 1)],
    "oldest": [("release_year", 1), ("title", 1)],
    "title": [("title", 1)],
    "added": [("date_added", -1), ("title", 1)],
}


def titles_col():
    return get_db()["titles"]


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def current_filters(args):
    """The non-empty filter values from the query string (used to keep filters across pages)."""
    keys = ("q", "type", "genre", "country", "rating", "year_from", "year_to", "sort")
    return {k: args.get(k, "").strip() for k in keys if args.get(k, "").strip()}


def build_query(f):
    query = {}
    if f.get("type") in TYPES:
        query["type"] = f["type"]
    if f.get("genre"):
        query["genres"] = f["genre"]
    if f.get("country"):
        query["countries"] = f["country"]
    if f.get("rating"):
        query["rating"] = f["rating"]
    lo, hi = to_int(f.get("year_from")), to_int(f.get("year_to"))
    if lo is not None or hi is not None:
        query["release_year"] = {}
        if lo is not None:
            query["release_year"]["$gte"] = lo
        if hi is not None:
            query["release_year"]["$lte"] = hi
    if f.get("q"):
        query["$text"] = {"$search": f["q"]}
    return query


def run_listing(endpoint, heading):
    filters = current_filters(request.args)
    query = build_query(filters)
    page = max(1, to_int(request.args.get("page")) or 1)
    titles = titles_col()

    total = titles.count_documents(query)
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, pages)

    if "$text" in query:
        cursor = titles.find(query, {"score": {"$meta": "textScore"}}).sort([("score", {"$meta": "textScore"})])
    else:
        cursor = titles.find(query).sort(SORTS.get(filters.get("sort"), SORTS["newest"]))
    items = list(cursor.skip((page - 1) * PER_PAGE).limit(PER_PAGE))

    return render_template(
        "titles.html", heading=heading, endpoint=endpoint, titles=items, total=total,
        page=page, pages=pages, filters=filters, types=TYPES,
        genres=sorted(titles.distinct("genres")),
        countries=sorted(titles.distinct("countries")),
        ratings=sorted(titles.distinct("rating")),
        sorts=list(SORTS),
    )


@app.errorhandler(PyMongoError)
def handle_db_error(err):
    return render_template("error.html", message=str(err)), 500


@app.route("/")
def index():
    return run_listing("index", "Browse titles")


@app.route("/search")
def search():
    return run_listing("search", "Search")


def get_title_or_404(title_id):
    try:
        doc = titles_col().find_one({"_id": ObjectId(title_id)})
    except InvalidId:
        abort(404)
    if doc is None:
        abort(404)
    return doc


@app.route("/title/<title_id>")
def detail(title_id):
    doc = get_title_or_404(title_id)
    rating_info = get_db()["ratings"].find_one({"code": doc.get("rating")})
    return render_template("detail.html", t=doc, rating_info=rating_info)


def clean_form(form):
    """Validate and normalise the add/edit form. Returns (document, error)."""
    title = form.get("title", "").strip()
    if not title:
        return None, "Title is required."
    kind = form.get("type", "")
    if kind not in TYPES:
        return None, "Type must be Movie or TV Show."
    year = to_int(form.get("release_year"))
    if year is None or not 1900 <= year <= 2100:
        return None, "Release year must be a number between 1900 and 2100."
    duration = to_int(form.get("duration_value"))
    if duration is not None and duration < 0:
        return None, "Duration cannot be negative."
    unit = "min" if kind == "Movie" else "Season(s)"
    return {
        "title": title[:200],
        "type": kind,
        "release_year": year,
        "rating": form.get("rating", "").strip().upper() or "NR",
        "duration_value": duration,
        "duration_unit": unit if duration is not None else "",
        "genres": split_list(form.get("genres")),
        "cast": split_list(form.get("cast")),
        "directors": split_list(form.get("directors")),
        "countries": split_list(form.get("countries")),
        "description": form.get("description", "").strip()[:1000],
    }, None


def form_values(doc=None):
    doc = doc or {}
    return {
        "title": doc.get("title", ""), "type": doc.get("type", "Movie"),
        "release_year": doc.get("release_year", ""), "rating": doc.get("rating", ""),
        "duration_value": doc.get("duration_value") if doc.get("duration_value") is not None else "",
        "genres": ", ".join(doc.get("genres", [])), "cast": ", ".join(doc.get("cast", [])),
        "directors": ", ".join(doc.get("directors", [])), "countries": ", ".join(doc.get("countries", [])),
        "description": doc.get("description", ""),
    }


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        data, error = clean_form(request.form)
        if error:
            flash(error, "error")
            return render_template("form.html", mode="add", v=request.form, types=TYPES), 400
        data["show_id"] = "app-" + str(ObjectId())
        data["date_added"] = datetime.now()
        try:
            result = titles_col().insert_one(data)
        except WriteError as exc:
            flash(f"Database rejected the document: {exc}", "error")
            return render_template("form.html", mode="add", v=request.form, types=TYPES), 400
        flash("Title added.", "success")
        return redirect(url_for("detail", title_id=result.inserted_id))
    return render_template("form.html", mode="add", v=form_values(), types=TYPES)


@app.route("/edit/<title_id>", methods=["GET", "POST"])
def edit(title_id):
    doc = get_title_or_404(title_id)
    if request.method == "POST":
        data, error = clean_form(request.form)
        if error:
            flash(error, "error")
            return render_template("form.html", mode="edit", t=doc, v=request.form, types=TYPES), 400
        try:
            titles_col().update_one({"_id": doc["_id"]}, {"$set": data})
        except WriteError as exc:
            flash(f"Database rejected the update: {exc}", "error")
            return render_template("form.html", mode="edit", t=doc, v=request.form, types=TYPES), 400
        flash("Title updated.", "success")
        return redirect(url_for("detail", title_id=doc["_id"]))
    return render_template("form.html", mode="edit", t=doc, v=form_values(doc), types=TYPES)


@app.route("/delete/<title_id>", methods=["POST"])
def delete(title_id):
    doc = get_title_or_404(title_id)
    titles_col().delete_one({"_id": doc["_id"]})
    flash(f"Deleted \"{doc['title']}\".", "success")
    return redirect(url_for("index"))


@app.route("/stats")
def stats():
    db = get_db()
    return render_template(
        "stats.html",
        total=db.titles.count_documents({}),
        types=analysis.type_counts(db),
        years=analysis.titles_per_year(db),
        duration=analysis.duration_stats(db),
        genres=analysis.top_genres(db),
        countries=analysis.top_countries(db),
        audiences=analysis.audience_groups(db),
    )


if __name__ == "__main__":
    try:
        get_db().command("ping")
    except PyMongoError as exc:
        raise SystemExit(f"\nCould not connect to MongoDB: {exc}\nStart MongoDB first, then run import_data.py.\n")
    app.run(debug=True)
