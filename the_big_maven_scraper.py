import asyncio
import re
from urllib.parse import urljoin
import aiohttp
import tempfile
import shutil
import os
import binascii
import unzip_http
import requests
import xml.etree.ElementTree as ET
import re
import sqlite3
import concurrent.futures
import resource
import time
from new_dload_apks import sha256sum

DB_PATH = "./the_base_of_datas.sqlite"
THREADS = 20
CONCURRENT_HTTP_CONNECTIONS = 100000

href_pattern = re.compile(r'href=["\']+(.*?)["\']+')


async def fetch(session, url):
    try:
        async with session.get(url) as response:
            return await response.text()
    except asyncio.TimeoutError:
        return ""


def extract_links(html, base_url):
    links = href_pattern.findall(html)
    return [base_url+link for link in links if not (link.startswith('../') or ":" in link)]

async def parse_directory(session, url):
    global aar_list
    html = await fetch(session, url)
    links = extract_links(html, url)
    for link in links:
        if link.endswith("aar"):
            aar_list += [link]
            print(f"Found aar {link}, total {len(aar_list)}")
    return list(filter(lambda x: x.endswith("/"), links))

async def gather_with_concurrency(n, *coros):
    # this is to avoid having too many open connections at the same time
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro
    return await asyncio.gather(*(sem_coro(c) for c in coros))

async def the_big_scrape(start_url):
    links = [start_url]
    while len(links):
        newlinks = []
        for x in range(0, len(links), CONCURRENT_HTTP_CONNECTIONS):
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                tasks = []
                for url in links[x:x+CONCURRENT_HTTP_CONNECTIONS]:
                    tasks += [parse_directory(session, url)]
                res = await gather_with_concurrency(CONCURRENT_HTTP_CONNECTIONS, *tasks)
                newlinks += [item for sublist in res for item in sublist]
        links = newlinks


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # example pom: https://repo.maven.apache.org/maven2/pl/droidsonroids/gif/android-gif-drawable/1.2.9/android-gif-drawable-1.2.9.pom
    cursor.execute('''CREATE TABLE IF NOT EXISTS maven_truth_modules
                    (id INTEGER PRIMARY KEY,
                    artifact TEXT,
                    groupname TEXT,
                    name TEXT,
                    url TEXT,
                    version TEXT,
                    repository TEXT,
                    developer TEXT,
                    date TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS maven_truth_hashes
                    (id INTEGER PRIMARY KEY,
                    hash BLOB,
                    relinked_hash BLOB,
                    name TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS maven_modules_hashes
                  (hash_id NOT_NULL, module_id NOT NULL,
                  PRIMARY KEY (hash_id, module_id),
                  FOREIGN KEY (hash_id) REFERENCES maven_truth_hashes (id),
                  FOREIGN KEY (module_id) REFERENCES maven_truth_modules (id)
               )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS maven_source
                   (module_id NOT NULL, source TEXT NOT NULL,
                   PRIMARY KEY (module_id, source),
                   FOREIGN KEY (module_id) REFERENCES maven_truth_modules (id)
               )''')

    conn.commit()
    conn.close()


def download_pom(url):
    listing = requests.get(url[:url.rfind("/")]).text
    date = re.findall(r"</a> *(\d*-\d*-\d* \d*:\d*)", listing)[0]

    xml = requests.get(url)
    if xml.status_code == 404:
        xml = requests.get(url.replace("-release", "").replace("-debug", ""))
    if xml.status_code != 200:
        print("ERROR EXIT CODE ", url, xml, xml.text)
        return None
    try:
        root = ET.fromstring(xml.text)
        ns = root.tag.split("}")[0]+"}"

        ret = {"url":url, "date":date, "developer":None}
        ret["artifact"] = root.find(ns+"artifactId").text if root.find(ns+"artifactId") is not None else None
        ret["groupname"] = root.find(ns+"groupId").text if root.find(ns+"groupId") is not None else None
        ret["version"] = root.find(ns+"version").text if root.find(ns+"version") is not None else None
        ret["name"] = root.find(ns+"name").text if root.find(ns+"name") is not None else None
        ret["repository"] = root.find(ns+"url").text if root.find(ns+"url") is not None else None
        ret["source"] = "maven central"
        if root.find(ns+"scm") is not None: # https://repo.maven.apache.org/maven2/app/alan/sdk/4.21.0/sdk-4.21.0.pom
            ret["repository"] = root.find(ns+"scm").find(ns+"url").text
        if root.find(ns+"developers") is not None:
            if root.find(ns+"developers").find(ns+"developer") is not None:
                if root.find(ns+"developers").find(ns+"developer").find(ns+"id") is not None:
                    ret["developer"] = root.find(ns+"developers").find(ns+"developer").find(ns+"id").text
                elif root.find(ns+"developers").find(ns+"developer").find(ns+"name") is not None:
                    ret["developer"] = root.find(ns+"developers").find(ns+"developer").find(ns+"name").text
        return ret
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        print(xml, xml.text)
        # os._exit(1)

def update_db_please_daddy(pom, dictionary_lib_name_hash):
    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()

    module_id = cursor.execute("SELECT id FROM maven_truth_modules WHERE url == (?) AND version == (?)",(pom["url"],pom["version"],)).fetchone()
    if not module_id:
        cursor.execute("INSERT INTO maven_truth_modules(artifact,groupname,name,url,version,repository,developer,date) VALUES (?,?,?,?,?,?,?,?) RETURNING id",(pom["artifact"],pom["groupname"],pom["name"],pom["url"],pom["version"],pom["repository"],pom["developer"], pom["date"]))
        module_id = cursor.fetchone()[0]
    else:
        module_id = module_id[0]

    for item in dictionary_lib_name_hash:
        lib_name, hash = item["name"], item["hash"]
        hash_id = cursor.execute('''SELECT id FROM maven_truth_hashes WHERE hash = ?''', (hash,)).fetchone()
        if not hash_id:
            hash_id = cursor.execute('''INSERT INTO maven_truth_hashes (hash,name) VALUES (?,?) RETURNING id''', (hash,lib_name)).fetchone()[0]
            print("maven lib", hash, " inserted with new id", hash_id)
        else:
            hash_id = hash_id[0]
        print(f"{hash=}, {lib_name=}, {module_id=}, {hash_id=}")
        cursor.execute('''INSERT OR REPLACE INTO maven_modules_hashes (hash_id, module_id) VALUES (?, ?)''', (hash_id, module_id))

    if "source" in pom:
        cursor.execute('''INSERT OR REPLACE INTO maven_source (module_id, source) VALUES (?, ?)''', (module_id, pom["source"]))

    conn.commit()
    conn.close()
    return module_id

def dload_libs_in_temp_dir(url, temp_libs):
    print(f"[..] downloading {url}")
    zipfile = unzip_http.RemoteZipFile(url)
    for file in zipfile.namelist():
        if file.startswith("jni/arm64") and not file.endswith("/"):
            # extract libraries
            with zipfile.open(file) as fpin:
                with open(temp_libs+"/"+file.rsplit("/")[-1], mode='wb') as fpout:
                    while True:
                        r = fpin.read(65536)
                        if not r: break
                        fpout.write(r)


def extract_libs_from_tmpdir(temp_libs):
    result = []
    for file in os.listdir(temp_libs):
        newfile = os.path.join(temp_libs,file)
        print(newfile)
        sha256 = sha256sum(newfile)
        if not os.path.exists("ground_truth_libs/"+sha256):
            shutil.move(newfile, "ground_truth_libs/"+sha256)
        if not sha256 in {item["hash"] for item in result}: # no duplicate hashes
            result += [{"name":file, "hash":sha256}]
    return result

def download_aar(url):
    temp_libs = tempfile.mkdtemp(prefix="acid_temp_libs_")
    try:
        if not os.path.exists("ground_truth_libs"): os.makedirs("ground_truth_libs")

        dload_libs_in_temp_dir(url, temp_libs)

        result = extract_libs_from_tmpdir(temp_libs)

        if not len(result): return []

        pom = download_pom(url[:-3] + "pom")

        if pom:
            try:
                return update_db_please_daddy(pom, result)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(e)
                os._exit(1)
            print("[+] done updating database")
        else:
            print("pom not found", url)

        return result
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        # os._exit(1)
    finally:
        shutil.rmtree(temp_libs)

# print(download_aar("https://repo.maven.apache.org/maven2/com/facebook/react/react-android/0.72.4/react-android-0.72.4-release.aar"))
# exit(1)

if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_NOFILE, (CONCURRENT_HTTP_CONNECTIONS*2, CONCURRENT_HTTP_CONNECTIONS*2))
    init_db()
    urls = ['https://repo.maven.apache.org/maven2/']

    if not os.path.exists("scraped_aar_list.txt"):
        aar_list = []
        for start_url in urls:
            if not start_url.endswith("/"): raise Exception("url needs to end with /")
            asyncio.run(the_big_scrape(start_url))
        open("scraped_aar_list.txt", "w").write("\n".join(aar_list))
    else:
        print("\x1b[31;1mFile scraped_aar_list.txt already exists, using that!\x1b[0m")
        aar_list = open("scraped_aar_list.txt", "r").read().split("\n")

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=THREADS)
    print("Spawning", THREADS, "threads...")
    for e,aar in enumerate(aar_list):
        while executor._work_queue.qsize() > THREADS*30: time.sleep(0.5)
        print(f"\x1b[31mDownloading aar {e} out of {len(aar_list)}\x1b[0m")
        executor.map(lambda p: download_aar(p), [aar], timeout=120)

    executor.shutdown()
