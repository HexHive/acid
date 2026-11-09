import csv
from itertools import takewhile
from collections import defaultdict
import os
import time
import sqlite3
import binascii
import requests
import shutil
import contextlib
import hashlib
import tempfile
import concurrent.futures
import unzip_http
import google_play_scraper, http
from elftools.elf.elffile import ELFFile

DEBUG_TEST = False
DB_PATH = "./the_base_of_datas.sqlite"
TARGET_DIR = "./apks"
try:
    ANDROZOO_API_KEY = os.environ["ANDROZOO_API_KEY"]
except KeyError as exc:
    raise RuntimeError("Environment variable ANDROZOO_API_KEY is not set") from exc
THREADS = 15

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS apps
                      (id INTEGER PRIMARY KEY, app_name TEXT, hash BLOB)
                   ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS libs
                      (id INTEGER PRIMARY KEY, hash BLOB, chash BLOB)
                   ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lib_names
                    (id INTEGER PRIMARY KEY, lib_id INTEGER, name TEXT,
                    FOREIGN KEY (lib_id) REFERENCES libs(id)
                   )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS app_libs
                      (app_id NOT_NULL, lib_id NOT NULL,
                      PRIMARY KEY (app_id, lib_id),
                      FOREIGN KEY (app_id) REFERENCES apps (id),
                      FOREIGN KEY (lib_id) REFERENCES libs (id)
                   )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS playstore_metadata
                    (app_id INTEGER,
                    downloads INTEGER,
                    rating FLOAT,
                    price FLOAT,
                    releasedate TEXT,
                    lastupdatedate TEXT,
                    updatetimestamp INTEGER,
                    genre TEXT,
                    developer_id INTEGER,
                    PRIMARY KEY (app_id),
                    FOREIGN KEY (app_id) REFERENCES apps (id),
                    FOREIGN KEY (developer_id) REFERENCES playstore_developer (id)
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS playstore_developer
                    (id INTEGER PRIMARY KEY,
                    google_play_id TEXT,
                    name TEXT,
                    email TEXT,
                    website TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS playstore_categories
                    (id INTEGER PRIMARY KEY,
                    app_id TEXT,
                    category TEXT,
                    FOREIGN KEY (app_id) REFERENCES apps(id)
                    )''')

    # those should have been primary keys from the start, but this mistake was done long ago, in forgotten times
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_apps_app_name ON apps (app_name)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_libs_hash ON libs (hash)''')
    conn.commit()
    conn.close()


def update_db_please_daddy(conn, app_name, dictionary_lib_name_hash, app_hash):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO apps (app_name, hash) VALUES (?, ?) RETURNING id", (app_name, app_hash))
    app_id = cursor.fetchone()[0]

    for item in dictionary_lib_name_hash:
        lib_name, hash, chash = item["name"], item["hash"], item["custom_hash"]
        lib_id = cursor.execute('''SELECT id FROM libs WHERE hash = ?''', (hash,)).fetchone()
        if not lib_id:
            lib_id = cursor.execute('''INSERT INTO libs (hash, chash) VALUES (?, ?) RETURNING id''', (hash, chash)).fetchone()
            print("lib", hash, " inserted with new id", lib_id)
        print(f"{hash=}, {app_name=}, {lib_name=}, {app_id=}, {lib_id=}")
        cursor.execute('''INSERT INTO app_libs (app_id, lib_id) VALUES (?, ?)''', (app_id, lib_id[0]))
        cursor.execute('''INSERT INTO lib_names (lib_id, name) VALUES (?, ?)''', (lib_id[0], lib_name))

    conn.commit()
    return app_id

def sha256sum(filename):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()

def custom_hash(filename):
    try:
        with open(filename, 'rb') as f:
            e = ELFFile(f)
            data = b''.join(s.data() for s in e.iter_sections() if s.name in ['.text', '.data', '.rodata'])
            return hashlib.sha256(data).hexdigest()
    except Exception as e:
        print(f"Error calculating custom hash of {filename}: {e}")
        return None


def is_app_already_dloaded(conn, app_name):
    cursor = conn.cursor()
    row = cursor.execute("SELECT id FROM apps WHERE app_name == (?)", (app_name,)).fetchone()
    if not row: return None
    return row[0]

def get_androozoo_csv():
    with contextlib.suppress(FileNotFoundError):
        os.remove("./latest.csv.gz")
    url = 'https://androzoo.uni.lu/static/lists/latest.csv.gz'
    local_filename = url.split('/')[-1]
    print("[..] downloading latest.csv from AndroZoo, around 3 GB to download")
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    print("[+] Download finished")
    os.system('gunzip ' + "./latest.csv.gz")
    os.system("head -n 10000 > latest_mini.csv")
    os.remove('./latest.csv.gz')


def getstuff(filename):
    with open(filename, "r") as csvfile:
        datareader = csv.reader(csvfile)
        print(next(datareader))
        yield next(datareader)  # yield the header row
        yield from takewhile(lambda r: True, datareader)
        return

# gets called with a list of appid ["com.example.hellolibs", "..."]
# returns a dict with the sha256 hashes of the newest app artifact in the zoo
def androzoo_get_latest_hashes():
    print("[..] getting the hash for the newest version for the apps...")
    gatheredData = defaultdict(lambda: (-1, ""))
    csv_file = "latest.csv"
    if DEBUG_TEST: 
        print("\x1b[33m[!] DEBUG TEST MODE ENABLED, using latest_mini.csv\x1b[0m")
        time.sleep(1)
        csv_file = "latest_mini.csv"
    for row in getstuff(csv_file):    # loop over csv file
        if row[6] == '': continue
        if int(row[6]) > gatheredData[row[5]][0]:
            gatheredData[row[5]] = (int(row[6]), row[0])
    result = {}

    if os.path.exists("broken_apks.txt"):
        ignored = open("broken_apks.txt", "r").read().split("\n")
    else:
        ignored = []

    for appid in gatheredData:
        if appid in ignored: print("ignoring", appid); continue
        result[appid] = binascii.unhexlify(gatheredData[appid][1])
    print("[+] finished collecting hashes for the apps!")
    return result


def download_and_extract_libs_from_apk(conn, appId, sha):
    temp_libs = tempfile.mkdtemp(prefix="acid_temp_libs_")
    try:
        if not os.path.exists("libs"): os.makedirs("libs")
        print(f"[..] downloading {appId}")
        sha = binascii.hexlify(sha).decode()

        zipfile = unzip_http.RemoteZipFile(f"https://androzoo.uni.lu/api/download?apikey={ANDROZOO_API_KEY}&sha256={sha}")
        for file in zipfile.namelist():
            if file.startswith("lib/arm64") and file[-1] != '/':
                with zipfile.open(file) as fpin:
                    with open(temp_libs+"/"+file.rsplit("/")[-1], mode='wb') as fpout:
                        while True:
                            r = fpin.read(65536)
                            if not r: break
                            fpout.write(r)

        result = []
        for file in os.listdir(temp_libs):
            newfile = os.path.join(temp_libs,file)
            sha256 = sha256sum(newfile)
            chash = custom_hash(newfile)
            chash = chash if chash else sha256  # fallback to sha256 if custom hash fails
            if not os.path.exists("libs/"+sha256):
                shutil.move(newfile, "libs/"+sha256)
            if not sha256 in {item["hash"] for item in result}: # no duplicate hashes
                result += [{"name":file, "hash":sha256, "custom_hash":chash}]

        try:
            return update_db_please_daddy(conn, appId, result, sha)
        except Exception as e:
            print(e)
        print("[+] done updating database")

        return result
    except Exception as e:
        print(f"https://androzoo.uni.lu/api/download?apikey={ANDROZOO_API_KEY}&sha256={sha}")
        print(e)
        import traceback
        traceback.print_exc()
    finally:
        shutil.rmtree(temp_libs)


def get_metadatas(conn, app_name, app_id):
    try: 
        cursor = conn.cursor()
        row = cursor.execute("SELECT app_id FROM playstore_metadata WHERE app_id == (?)", (app_id,)).fetchone()
        if row: 
            print("metadata for ", app_name, "already downloaded")
            return

        row = cursor.execute("SELECT * FROM app_libs WHERE app_id == (?)", (app_id,)).fetchone()
        if not row:
            print("app_id", app_id, "not found in app_libs, skipping metadata download")
            return

        print("Fetching metadata for app_id", app_id)

        
        result = google_play_scraper.app(app_name)
        print(f"Found metadata for app {app_name}, downloads {result['realInstalls']}")
        if result['score'] == None: result['score'] = 0

        dev_id = cursor.execute('''SELECT id FROM playstore_developer WHERE name = ?''', (result['developer'],)).fetchone()
        if not dev_id:
            dev_id = cursor.execute('''INSERT INTO playstore_developer (google_play_id, name, email, website) VALUES (?, ?, ?, ?) RETURNING id''', (result['developerId'], result['developer'], result['developerEmail'], result['developerWebsite'])).fetchone()
        cursor.execute('''INSERT INTO playstore_metadata VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            int(app_id),
            int(result['realInstalls']),
            float(result['score']),
            float(result['price']),
            str(result['released']),
            str(result['lastUpdatedOn']),
            int(result['updated']),
            str(result['genre']),
            int(dev_id[0]),
        ))
        for category in result['categories']:
            cursor.execute('''INSERT INTO playstore_categories (app_id, category) VALUES (?, ?)''', (app_id, category['id']))

        conn.commit()
       
    except google_play_scraper.exceptions.NotFoundError:
        print(app_name, "404, app not found...")
    except http.client.InvalidURL:
        print(app_name, "invalid URL...")
    except google_play_scraper.exceptions.ExtraHTTPError:
        print(app_name, "503, app not found")
    except Exception as e:
        print(e)

def get_app_and_metadata(app_name, hash):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        app_id = is_app_already_dloaded(conn, app_name)
        if app_id == None: 
            app_id = download_and_extract_libs_from_apk(conn, app_name, hash)
        if app_id:
            get_metadatas(conn, app_name, app_id)
    except sqlite3.OperationalError as e:
        print("Database error:", e)
        print("Retrying in 5 seconds...")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    if not os.path.exists("latest.csv"):
        get_androozoo_csv()

    hashes = androzoo_get_latest_hashes()
    print("Preparing", len(hashes), "hashes to be downloaded...")

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=THREADS)
    print("Spawning", THREADS, "threads...")
    for app_name, hash in hashes.items():
        while executor._work_queue.qsize() > THREADS*300: time.sleep(0.5)
        executor.map(lambda p: get_app_and_metadata(*p), [(app_name, hash)])

    executor.shutdown()
