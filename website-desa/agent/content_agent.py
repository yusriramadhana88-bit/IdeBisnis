import os
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime, date

import dropbox
import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

DBX_TOKEN = os.environ["DROPBOX_ACCESS_TOKEN"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

dbx = dropbox.Dropbox(DBX_TOKEN)
claude = anthropic.Anthropic()

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger("desa-agent")

DROPBOX_ROOT = "/website-desa"
LOCAL_CONTENT = Path(__file__).parent.parent / "content"
PROCESSED_LOG = LOCAL_CONTENT / ".processed.json"

CALENDAR_EVENTS = {
    "01-01": "Tahun Baru",
    "02-14": "Hari Valentine",
    "03-08": "Hari Perempuan Internasional",
    "04-21": "Hari Kartini",
    "05-01": "Hari Buruh",
    "05-02": "Hari Pendidikan Nasional",
    "05-20": "Hari Kebangkitan Nasional",
    "06-01": "Hari Lahir Pancasila",
    "06-05": "Hari Lingkungan Hidup",
    "08-17": "Hari Kemerdekaan RI",
    "10-05": "Hari Tentara Nasional",
    "10-28": "Hari Sumpah Pemuda",
    "11-10": "Hari Pahlawan",
    "12-22": "Hari Ibu",
    "12-25": "Hari Natal",
}

CONTENT_PROMPT = """Kamu adalah content writer untuk website desa resmi di Indonesia.
Desa: {village_name}, Kecamatan {kecamatan}, Kabupaten {kabupaten}, Provinsi {provinsi}.

Tugas: Buat artikel/berita untuk website desa berdasarkan informasi berikut.

{context}

Aturan:
- Bahasa Indonesia formal tapi ramah
- Sertakan detail tanggal, tempat, pelaku jika tersedia
- Jika ini terkait event nasional, kaitkan dengan kegiatan desa
- Panjang 200-400 kata
- Format output JSON:
{{
  "title": "Judul artikel",
  "category": "Berita|Pengumuman|Agenda|Profil|Galeri",
  "content_html": "<p>Paragraf 1...</p><p>Paragraf 2...</p>",
  "excerpt": "Ringkasan 1-2 kalimat",
  "tags": ["tag1", "tag2"],
  "publish_date": "YYYY-MM-DD"
}}

Jawab HANYA dengan JSON.
"""

CALENDAR_PROMPT = """Kamu adalah content planner untuk website desa resmi.
Desa: {village_name}.

Event nasional yang akan datang dalam 7 hari: {event_name} ({event_date}).

Buat artikel ucapan/peringatan dari pemerintah desa untuk event ini.
Kaitkan dengan konteks desa (masyarakat pedesaan, gotong royong, dll).

Format output JSON:
{{
  "title": "Judul artikel",
  "category": "Berita",
  "content_html": "<p>Paragraf...</p>",
  "excerpt": "Ringkasan 1-2 kalimat",
  "tags": ["tag1", "tag2"],
  "publish_date": "{event_date}"
}}

Jawab HANYA dengan JSON.
"""


def load_processed():
    if PROCESSED_LOG.exists():
        return json.loads(PROCESSED_LOG.read_text())
    return {}


def save_processed(data):
    PROCESSED_LOG.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_LOG.write_text(json.dumps(data, indent=2))


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


def list_village_folders() -> list[str]:
    try:
        result = dbx.files_list_folder(DROPBOX_ROOT)
        return [e.name for e in result.entries if isinstance(e, dropbox.files.FolderMetadata)]
    except dropbox.exceptions.ApiError:
        log.error(f"Cannot access {DROPBOX_ROOT}")
        return []


def scan_new_files(village_folder: str, processed: dict) -> list[dict]:
    path = f"{DROPBOX_ROOT}/{village_folder}"
    new_files = []

    try:
        result = dbx.files_list_folder(path, recursive=True)
        entries = result.entries
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)
    except dropbox.exceptions.ApiError:
        return []

    for entry in entries:
        if not isinstance(entry, dropbox.files.FileMetadata):
            continue
        ext = Path(entry.name).suffix.lower()
        if ext not in (".txt", ".docx", ".jpg", ".jpeg", ".png", ".pdf"):
            continue

        fkey = f"{village_folder}:{entry.path_lower}"
        if fkey in processed:
            continue

        new_files.append({
            "key": fkey,
            "path": entry.path_lower,
            "name": entry.name,
            "ext": ext,
            "modified": entry.server_modified.isoformat(),
            "village": village_folder,
        })

    return new_files


def download_file(path: str) -> bytes:
    _, response = dbx.files_download(path)
    return response.content


def generate_article(village_config: dict, context: str) -> dict:
    import re
    prompt = CONTENT_PROMPT.format(
        village_name=village_config["name"],
        kecamatan=village_config.get("kecamatan", "-"),
        kabupaten=village_config.get("kabupaten", "-"),
        provinsi=village_config.get("provinsi", "-"),
        context=context,
    )
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def generate_calendar_article(village_config: dict, event_name: str, event_date: str) -> dict:
    import re
    prompt = CALENDAR_PROMPT.format(
        village_name=village_config["name"],
        event_name=event_name,
        event_date=event_date,
    )
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def save_article(village: str, article: dict):
    out_dir = LOCAL_CONTENT / village / date.today().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = article["title"].lower().replace(" ", "-")[:50]
    filepath = out_dir / f"{slug}.json"
    filepath.write_text(json.dumps(article, indent=2, ensure_ascii=False))
    log.info(f"Article saved: {filepath}")
    return filepath


def check_upcoming_events(village_config: dict, processed: dict, days_ahead: int = 7):
    today = date.today()
    articles = []
    for offset in range(days_ahead + 1):
        d = date(today.year, today.month, today.day)
        from datetime import timedelta
        check_date = today + timedelta(days=offset)
        key = check_date.strftime("%m-%d")
        cal_key = f"calendar:{village_config['folder']}:{check_date.isoformat()}"

        if key in CALENDAR_EVENTS and cal_key not in processed:
            event_name = CALENDAR_EVENTS[key]
            log.info(f"Upcoming event: {event_name} on {check_date}")
            article = generate_calendar_article(
                village_config, event_name, check_date.isoformat()
            )
            save_article(village_config["folder"], article)
            processed[cal_key] = {"event": event_name, "generated_at": datetime.now().isoformat()}
            articles.append(article)

    return articles


def process_text_file(village_config: dict, content: bytes, filename: str) -> dict:
    text = content.decode("utf-8", errors="replace")
    context = f"File '{filename}' berisi informasi berikut:\n\n{text}"
    return generate_article(village_config, context)


def process_image_file(village_config: dict, content: bytes, filename: str) -> dict:
    import base64
    b64 = base64.standard_b64encode(content).decode()
    ext = Path(filename).suffix.lower()
    media_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

    import re
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": CONTENT_PROMPT.format(
                    village_name=village_config["name"],
                    kecamatan=village_config.get("kecamatan", "-"),
                    kabupaten=village_config.get("kabupaten", "-"),
                    provinsi=village_config.get("provinsi", "-"),
                    context="Buat artikel berdasarkan foto kegiatan desa ini. Deskripsikan apa yang terlihat di foto.",
                )},
            ],
        }],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def run_agent(villages: list[dict], interval_minutes: int = 30):
    log.info(f"Desa Agent started. Monitoring {len(villages)} desa(s).")
    LOCAL_CONTENT.mkdir(parents=True, exist_ok=True)

    while True:
        processed = load_processed()

        for vc in villages:
            folder = vc["folder"]
            log.info(f"Scanning: {folder}")

            new_files = scan_new_files(folder, processed)
            for f in new_files:
                log.info(f"New file: {f['name']}")
                try:
                    content = download_file(f["path"])

                    if f["ext"] == ".txt":
                        article = process_text_file(vc, content, f["name"])
                    elif f["ext"] in (".jpg", ".jpeg", ".png"):
                        article = process_image_file(vc, content, f["name"])
                    else:
                        log.info(f"Skipping unsupported: {f['ext']}")
                        processed[f["key"]] = {"skipped": True}
                        continue

                    save_article(folder, article)
                    processed[f["key"]] = {
                        "generated_at": datetime.now().isoformat(),
                        "title": article.get("title"),
                    }
                except Exception as e:
                    log.error(f"Error processing {f['name']}: {e}")
                    processed[f["key"]] = {"error": str(e)}

            check_upcoming_events(vc, processed)

        save_processed(processed)
        log.info(f"Sleeping {interval_minutes} minutes...")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    villages = [
        {
            "folder": "desa-berat-wetan",
            "name": "Desa Berat Wetan",
            "kecamatan": "Kalidawir",
            "kabupaten": "Tulungagung",
            "provinsi": "Jawa Timur",
        },
    ]
    run_agent(villages)
