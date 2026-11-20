"""Run all five analyses, print result tables and (if matplotlib is installed) save charts to outputs/.

Usage:  python run_analysis.py
Use the printed tables and the PNG files in outputs/ to fill in Section 7 of the project report.
"""
import os

import analysis
from db import DB_NAME, get_db

OUT = "outputs"


def table(title, headers, rows):
    print(f"\n{title}")
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)] if rows else [len(h) for h in headers]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line + "\n" + "-" * len(line))
    for r in rows:
        print("  ".join(str(x).ljust(w) for x, w in zip(r, widths)))


def save_charts(results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed - skipping charts. pip install matplotlib)")
        return
    os.makedirs(OUT, exist_ok=True)

    def bar(name, title, labels, values, horizontal=False, xlabel="", ylabel=""):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        if horizontal:
            ax.barh(labels[::-1], values[::-1], color="#d92d3a")
        else:
            ax.bar(labels, values, color="#d92d3a")
        ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
        fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=150); plt.close(fig)

    t = results["types"]
    bar("type_counts", "Movies vs TV Shows", [r["_id"] for r in t], [r["count"] for r in t], ylabel="Titles")
    y = results["years"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot([r["_id"] for r in y], [r["count"] for r in y], marker="o", color="#d92d3a")
    ax.set_title("Titles per release year"); ax.set_xlabel("Release year"); ax.set_ylabel("Titles")
    fig.tight_layout(); fig.savefig(f"{OUT}/titles_per_year.png", dpi=150); plt.close(fig)
    g = results["genres"]
    bar("top_genres", "Top 10 genres", [r["_id"] for r in g], [r["titles"] for r in g], True, xlabel="Titles")
    c = results["countries"]
    bar("top_countries", "Top 10 countries", [r["_id"] for r in c], [r["titles"] for r in c], True, xlabel="Titles")
    a = results["audiences"]
    bar("audience_groups", "Titles by audience group", [r["_id"] for r in a], [r["titles"] for r in a], ylabel="Titles")
    ip = results["index"]
    bar("index_docs_examined", f"Documents examined (release_year = {ip['year']})", ["Before index", "After index"],
        [ip["before"]["docs_examined"], ip["after"]["docs_examined"]], ylabel="Documents examined")
    print(f"\nCharts saved to {OUT}/")


def main():
    db = get_db()
    results = {
        "types": analysis.type_counts(db), "years": analysis.titles_per_year(db),
        "duration": analysis.duration_stats(db), "genres": analysis.top_genres(db),
        "countries": analysis.top_countries(db), "audiences": analysis.audience_groups(db),
        "index": analysis.index_performance(db),
    }
    print(f"Database: {DB_NAME}   titles: {db.titles.count_documents({})}")

    table("Table 7.1  Titles by type", ["Type", "Titles"], [(r["_id"], r["count"]) for r in results["types"]])
    table("Table 7.2  Titles per release year (latest 10 years)", ["Year", "Titles"],
          [(r["_id"], r["count"]) for r in results["years"]])
    d = results["duration"]
    table("Table 7.3  Movie duration (minutes)", ["Statistic", "Value"],
          [("Average", round(d["avg_minutes"], 1)), ("Shortest", d["shortest"]), ("Longest", d["longest"])])
    table("Table 7.4  Top 10 genres", ["Rank", "Genre", "Titles"],
          [(i, r["_id"], r["titles"]) for i, r in enumerate(results["genres"], 1)])
    table("Top 10 countries", ["Rank", "Country", "Titles"],
          [(i, r["_id"], r["titles"]) for i, r in enumerate(results["countries"], 1)])
    table("Table 7.5  Titles by audience group", ["Audience group", "Titles"],
          [(r["_id"], r["titles"]) for r in results["audiences"]])
    ip = results["index"]
    table(f"Table 7.6  Query: release_year == {ip['year']}", ["Metric", "Before index", "After index"], [
        ("Winning plan stage", ip["before"]["stage"], ip["after"]["stage"]),
        ("totalDocsExamined", ip["before"]["docs_examined"], ip["after"]["docs_examined"]),
        ("nReturned", ip["before"]["returned"], ip["after"]["returned"]),
        ("executionTimeMillis", ip["before"]["millis"], ip["after"]["millis"]),
    ])
    save_charts(results)


if __name__ == "__main__":
    main()
