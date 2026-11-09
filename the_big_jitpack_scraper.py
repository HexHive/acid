import asyncio
import re
import aiohttp
import tempfile
import shutil
import os
import json
import requests
import xml.etree.ElementTree as ET
import concurrent.futures
import resource
import time
import datetime
import sqlite3
from the_big_maven_scraper import extract_libs_from_tmpdir, init_db, dload_libs_in_temp_dir, gather_with_concurrency

DB_PATH = "./the_base_of_datas.sqlite"
THREADS = 10
CONCURRENT_HTTP_CONNECTIONS = 50

build_dates = {}

# hacked version of update_db_please_daddy
# because I need to replace the dates of the maven modules
# please delete this as soon as you see this comment
# and use the one imported from the_big_maven_scraper
def update_db_please_daddy(pom, dictionary_lib_name_hash):
    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()

    module_id = cursor.execute("SELECT id FROM maven_truth_modules WHERE url == (?) AND version == (?)",(pom["url"],pom["version"],)).fetchone()
    if not module_id:
        cursor.execute("INSERT INTO maven_truth_modules(artifact,groupname,name,url,version,repository,developer,date) VALUES (?,?,?,?,?,?,?,?) RETURNING id",(pom["artifact"],pom["groupname"],pom["name"],pom["url"],pom["version"],pom["repository"],pom["developer"], pom["date"]))
        module_id = cursor.fetchone()[0]
    else:
        module_id = module_id[0]
        cursor.execute("REPLACE INTO maven_truth_modules(id,artifact,groupname,name,url,version,repository,developer,date) VALUES (?,?,?,?,?,?,?,?,?)",(module_id, pom["artifact"],pom["groupname"],pom["name"],pom["url"],pom["version"],pom["repository"],pom["developer"], pom["date"]))

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


async def fetch(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 429:
                print("\x1b[31mToo many requests! Quitting...\x1b[0m")
                exit(1)
            return await response.text()
    except asyncio.TimeoutError:
        return ""
    except aiohttp.client_exceptions.ClientPayloadError:
        return ""

def download_pom(url):
    # build dates we get from the 
    date = build_dates[url[:-3]+"aar"]

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
        ret["source"] = "jitpack"
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


def download_aar(url):
    temp_libs = tempfile.mkdtemp(prefix="acid_temp_libs_")
    try:
        if not os.path.exists("ground_truth_libs"): os.makedirs("ground_truth_libs")

        dload_libs_in_temp_dir(url, temp_libs)

        result = extract_libs_from_tmpdir(temp_libs)

        if not len(result): return []

        pom = download_pom(url[:-3] + "pom")

        print(pom)

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
        print("failure url:", url) 
        print(e)
        import traceback
        traceback.print_exc()
        # os._exit(1)
    finally:
        shutil.rmtree(temp_libs)


async def find_jitpack_links(session, url):
    html = await fetch(session, url)
    jitpacks = re.findall(r"https?://jitpack.io/#[^\s<>[\]()'\"`,;]+[^\s<>[\]()'\"`\",;.]", html)
    print(jitpacks)
    if not len(jitpacks): 
        print("No jitpacks found")
        print(url)
        print(html)
    return jitpacks

async def find_jitpack_versions(session, url):
    result = []
    package_name = url.split("#")[-1]
    package_name = re.findall(r"^.*?/[^/]*", package_name)
    if len(package_name): package_name = package_name[0]
    else: return []
    if "." in package_name.split("/")[0]:
        api_versions_url = f"https://jitpack.io/api/versions/{package_name}"
    else:
        api_versions_url = f"https://jitpack.io/api/versions/com.github.{package_name}"
    html = await fetch(session, api_versions_url)
    try:
        res_dict = json.loads(html)
    except Exception:
        print("Error getting json")
        print(package_name)
        print(api_versions_url)
        return []
    for package_name,wrapper in res_dict.items():
        for real_package_name, data in wrapper.items():
            for version, version_data in data.items():
                # if not version_data['isTag']: continue
                result += [f"https://jitpack.io/{package_name.replace('.','/')}/{real_package_name}/{version}/build.log"]
    return result

async def find_aar_links(session, url):
    global build_dates
    result = []
    html = await fetch(session, url)
    lines = html.split('\n')
    try:
        files_line = lines.index("Files: ")
    except ValueError:
        return []

    for line in lines[files_line:]:
        if line.endswith(".aar"):
            result += ["https://jitpack.io/"+line]

    date_line = re.findall(r"Start: .* UTC 20..", html)
    if len(date_line):
        print(date_line)
        input_date = datetime.datetime.strptime(date_line[0].replace('UTC', ''), 'Start: %a %b %d %H:%M:%S %Y')
        date = input_date.strftime('%Y-%m-%d %H:%M:%S')
        print("Inserting URL", url, "with date", date)
        for l in result:
            build_dates[l] = date
    return result



async def the_big_scrape2(urls):
    jitpack_links = []
    for x in range(0, len(urls), CONCURRENT_HTTP_CONNECTIONS):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            tasks = []
            for url in urls[x:x+CONCURRENT_HTTP_CONNECTIONS]:
                tasks += [find_jitpack_links(session, url)]
            res = await gather_with_concurrency(CONCURRENT_HTTP_CONNECTIONS, *tasks)
            jitpack_links += [item for sublist in res for item in sublist]

    jitpack_links = list(set(jitpack_links))

    print("Number of extracted jitpack links:", len(jitpack_links))

    build_logs = []
    for x in range(0, len(jitpack_links), CONCURRENT_HTTP_CONNECTIONS):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            tasks = []
            for link in jitpack_links[x:x+CONCURRENT_HTTP_CONNECTIONS]:
                tasks += [find_jitpack_versions(session, link)]
            res = await gather_with_concurrency(CONCURRENT_HTTP_CONNECTIONS, *tasks)
            build_logs += [item for sublist in res for item in sublist]

    print("Number of build logs to download:", len(build_logs))

    aar_list = []
    for x in range(0, len(build_logs), CONCURRENT_HTTP_CONNECTIONS):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            tasks = []
            for link in build_logs[x:x+CONCURRENT_HTTP_CONNECTIONS]:
                tasks += [find_aar_links(session, link)]
            res = await gather_with_concurrency(CONCURRENT_HTTP_CONNECTIONS, *tasks)
            aar_list += [item for sublist in res for item in sublist]

    return aar_list





if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_NOFILE, (CONCURRENT_HTTP_CONNECTIONS*40, CONCURRENT_HTTP_CONNECTIONS*40))

    if not os.path.exists("sourcegraph_jitpack_search.csv"):
        print("Please export search results from https://sourcegraph.com/search?q=https://jitpack.io/%23&patternType=keyword&sm=0")
        print("And save them in sourcegraph_jitpack_search.csv")
        raise Exception("sourcegraph_jitpack_search.csv not found")

    urls = []
    with open("sourcegraph_jitpack_search.csv", "r") as f:
        aar_list = f.read().split("\n")[1:] #skip header
    files_list = [x.split(",") for x in aar_list]
    for file in files_list[:]:
        if not len(file[0]): continue
        url = file[4]
        new_url = url.replace("/-/blob/", "/-/raw/")
        urls += [new_url]

    aar_list = list(set(asyncio.run(the_big_scrape2(urls))))
    with open("scraped_jitpack_aar_list.txt", "w") as f:
        f.write("\n".join(aar_list))

    init_db() 

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=THREADS)
    print("Spawning", THREADS, "threads...")
    for e,aar in enumerate(aar_list):
        while executor._work_queue.qsize() > THREADS*30: time.sleep(0.5)
        print(f"\x1b[31mDownloading aar {e} out of {len(aar_list)}\x1b[0m")
        executor.map(lambda p: download_aar(p), [aar], timeout=120)

    executor.shutdown()
