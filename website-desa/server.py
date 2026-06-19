import json
from pathlib import Path
from flask import Flask, render_template, jsonify

app = Flask(__name__, template_folder="templates", static_folder="templates/static")

CONTENT_DIR = Path(__file__).parent / "content"


def load_articles(village: str, limit: int = 10) -> list[dict]:
    village_dir = CONTENT_DIR / village
    if not village_dir.exists():
        return []

    articles = []
    for date_dir in sorted(village_dir.iterdir(), reverse=True):
        if not date_dir.is_dir() or date_dir.name.startswith("."):
            continue
        for f in date_dir.glob("*.json"):
            articles.append(json.loads(f.read_text()))
            if len(articles) >= limit:
                return articles
    return articles


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/articles")
def api_articles():
    articles = load_articles("desa-berat-wetan")
    return jsonify(articles)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
