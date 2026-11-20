"""Generate a small SYNTHETIC CSV in the same layout as netflix_titles.csv, for trying the app
before you download the real dataset. Do not use its numbers in your report.

Usage:  python make_sample_csv.py        ->  data/sample_netflix_titles.csv
"""
import csv
import random

rng = random.Random(42)
ADJ = ["Silent", "Golden", "Broken", "Hidden", "Last", "Electric", "Midnight", "Crimson", "Wild", "Lost", "Bright", "Frozen"]
NOUN = ["River", "Kingdom", "Letters", "Harbor", "Garden", "Signal", "Promise", "Horizon", "Mirror", "Journey", "Empire", "Season"]
GENRES_MOVIE = ["Dramas", "Comedies", "Documentaries", "Action & Adventure", "International Movies", "Thrillers", "Romantic Movies", "Horror Movies"]
GENRES_SHOW = ["TV Dramas", "International TV Shows", "Crime TV Shows", "Kids' TV", "Reality TV", "Anime Series", "Docuseries"]
COUNTRIES = ["United States", "India", "United Kingdom", "Japan", "South Korea", "France", "Canada", "Spain", "Brazil", "Germany"]
RATINGS = ["TV-MA", "TV-14", "TV-PG", "R", "PG-13", "PG", "TV-Y7", "TV-G", "G", "TV-Y", "NR"]
FIRST = ["Aarav", "Maya", "Liam", "Sofia", "Kenji", "Hana", "Noah", "Priya", "Lucas", "Amara", "Diego", "Zoe"]
LAST = ["Sharma", "Kim", "Silva", "Brown", "Tanaka", "Garcia", "Singh", "Martin", "Okafor", "Rossi"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

person = lambda: f"{rng.choice(FIRST)} {rng.choice(LAST)}"
rows = []
for i in range(1, 401):
    is_movie = rng.random() < 0.7
    n_genres = rng.randint(1, 3)
    rows.append({
        "show_id": f"s{i}",
        "type": "Movie" if is_movie else "TV Show",
        "title": f"{rng.choice(ADJ)} {rng.choice(NOUN)} {i}",
        "director": ", ".join(person() for _ in range(rng.randint(1, 2))) if rng.random() < 0.8 else "",
        "cast": ", ".join(person() for _ in range(rng.randint(2, 6))) if rng.random() < 0.9 else "",
        "country": ", ".join(rng.sample(COUNTRIES, rng.randint(1, 2))) if rng.random() < 0.92 else "",
        "date_added": f"{rng.choice(MONTHS)} {rng.randint(1, 28)}, {rng.randint(2015, 2021)}" if rng.random() < 0.97 else "",
        "release_year": rng.randint(2000, 2021),
        "rating": rng.choice(RATINGS),
        "duration": f"{rng.randint(70, 160)} min" if is_movie else f"{rng.randint(1, 6)} Season" + ("s" if rng.random() < .6 else ""),
        "listed_in": ", ".join(rng.sample(GENRES_MOVIE if is_movie else GENRES_SHOW, n_genres)),
        "description": f"A {rng.choice(ADJ).lower()} story about {rng.choice(NOUN).lower()} and the people around it.",
    })

# Messy cases like the real file: leading spaces, rating/duration mix-up, blank rating, duplicate id.
rows[3]["date_added"] = " " + rows[3]["date_added"]
rows[10].update(rating="74 min", duration="", type="Movie", listed_in="Documentaries")
rows[11].update(rating="", cast="Maya Kim,, Zoe Rossi,")
rows.append(dict(rows[5]))  # duplicate show_id

with open("data/sample_netflix_titles.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"wrote data/sample_netflix_titles.csv ({len(rows)} rows, synthetic)")
