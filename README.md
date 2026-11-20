# MovieVault

Explore the **Netflix Movies and TV Shows** dataset with **Flask + PyMongo + MongoDB**.
Browse, search and filter titles, add / edit / delete records, and view aggregation-based statistics.

## 1. Prerequisites

- Python 3.10+
- MongoDB Community Server running locally (`mongodb://localhost:27017`)
- The dataset (below)

## 2. Get the dataset

1. Open https://www.kaggle.com/datasets/shivamb/netflix-shows (free Kaggle account needed) and download it.
2. Unzip and put **`netflix_titles.csv`** in the `data/` folder.

Want to try the app first? `python make_sample_csv.py` creates a small **synthetic** file,
`data/sample_netflix_titles.csv`. Use it to test only, never for the numbers in your report.

## 3. Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # optional: change MONGO_URI / DB_NAME
```

## 4. Import the data

```bash
python import_data.py                                  # uses data/netflix_titles.csv
python import_data.py --csv data/sample_netflix_titles.csv
```

This **drops and recreates** the `titles` and `ratings` collections, cleans the data, adds a schema
validator and the indexes, and prints a data-quality summary (use it for Table 5.1 of the report).

## 5. Run the web app

```bash
python app.py
```

Open http://127.0.0.1:5000

| Route | Purpose |
|---|---|
| `/` | Browse titles (paginated, 24 per page) with filters |
| `/search` | Same listing, titled "Search": text search + type, genre, country, rating, year range, sort |
| `/title/<id>` | Detail page (rating description comes from `ratings`) |
| `/add`, `/edit/<id>`, `/delete/<id>` | Create, update, delete |
| `/stats` | Aggregation charts: type, titles per year, top genres/countries, audience groups |

## 6. Run the analyses for the report

```bash
python run_analysis.py
```

Prints Tables 7.1 to 7.6 (type counts, titles per year, duration stats, top genres/countries,
audience groups via `$lookup`, and before/after index `explain()` statistics) and saves PNG charts in `outputs/`.
Copy the numbers and charts into Section 7 of the report.

## 7. Tests

```bash
python tests/test_cleaning.py       # cleaning logic, needs only pandas
```

## Project layout

```
movievault/
├── app.py               Flask routes
├── analysis.py          The five analyses (aggregation pipelines, explain)
├── cleaning.py          CSV cleaning + ratings reference data (pure Python)
├── import_data.py       CSV -> MongoDB (validator + indexes)
├── run_analysis.py      Prints result tables, saves charts
├── db.py                MongoClient / database handle
├── make_sample_csv.py   Synthetic test data generator
├── data/                Put netflix_titles.csv here
├── templates/ static/   Pages and styling
└── tests/
```

## Data model

`titles` (one document per title):

```json
{
  "show_id": "s1", "type": "Movie", "title": "...",
  "directors": ["..."], "cast": ["..."], "countries": ["..."],
  "date_added": "ISODate", "release_year": 2019, "rating": "TV-MA",
  "duration_value": 112, "duration_unit": "min",
  "genres": ["Dramas", "Comedies"], "description": "..."
}
```

`ratings` (one document per rating code): `{ "code": "TV-MA", "description": "...", "audience_group": "Adults" }`

Indexes: unique `show_id`, text on `title` + `description`, multikey `genres`, `release_year`, `type`.

## Try the queries in mongosh

```js
use movievault
db.titles.find({type: "Movie", genres: "Documentaries"}, {title: 1, release_year: 1}).limit(5)
db.titles.aggregate([{$unwind: "$genres"}, {$group: {_id: "$genres", n: {$sum: 1}}}, {$sort: {n: -1}}, {$limit: 5}])
db.titles.find({release_year: 2018}).explain("executionStats")
```

## Troubleshooting

- **"Could not connect to MongoDB"**: start the MongoDB service (`mongod`) and check `MONGO_URI`.
- **Empty pages**: run `python import_data.py` first.
- **Charts don't draw on /stats**: they load Chart.js from a CDN, so the browser needs internet access.
