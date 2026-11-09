import asyncio
import re
import aiohttp
import tempfile
import shutil
import os
import io
import tarfile
import zipfile
import requests
import xml.etree.ElementTree as ET
import sqlite3
import concurrent.futures
import resource
import time
import json
import string
import random
from datetime import datetime
from new_dload_apks import sha256sum
from the_big_maven_scraper import update_db_please_daddy, extract_libs_from_tmpdir, init_db


DB_PATH = "./the_base_of_datas.sqlite"
THREADS = 10
CONCURRENT_HTTP_CONNECTIONS = 100000


def dload_libs_in_temp_dir(url, temp_libs):
    print(f"[..] downloading {url}")
    tar_file = requests.get(url).content
    with tarfile.open(fileobj=io.BytesIO(tar_file), mode='r') as tar:
        for member in tar.getmembers():
            if member.name.endswith("flutter.jar"):
                print(member.name)
                zip_file_like = io.BytesIO(tar.extractfile(member).read())
                with zipfile.ZipFile(zip_file_like, 'r') as zipf:
                    for zip_member in zipf.namelist():
                        if zip_member.startswith("lib/arm64-v8a/") and not zip_member.endswith("/"):
                            target_path = os.path.join(temp_libs,os.path.basename(zip_member))
                            with zipf.open(zip_member) as file_data, open(target_path, 'wb') as output_file:
                                output_file.write(file_data.read())
                            os.system(f"mv {target_path} {temp_libs}/$(sha256sum {target_path} | cut -d ' ' -f 1)")
                            print(f'Extracted file from zip: {zip_member} to {target_path}')

# version='v0.1.6'
# archive='dev/linux/flutter_linux_v0.1.6-dev.tar.xz'
# date='2018-02-27T00:26:37.058993Z'

def download_aar(version):
    temp_libs = tempfile.mkdtemp(prefix="acid_temp_libs_")
    try:
        if not os.path.exists("ground_truth_libs"): os.makedirs("ground_truth_libs")

        version, url, date = version[0], flutter_download_url + version[1], version[2]
        dload_libs_in_temp_dir(url, temp_libs)

        result = extract_libs_from_tmpdir(temp_libs)

        print(result)

        if not len(result): return []

        pom = {}
        pom["url"] = flutter_archive_url
        pom["date"] = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M")
        pom["artifact"] = "flutter"
        pom["groupname"] = "com.google.flutter"
        pom["version"] = version
        pom["name"] = "flutter"
        pom["repository"] = "https://github.com/flutter/flutter"
        pom["developer"] = "google"
        pom["source"] = "flutter"

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


def get_flutter_versions():
    response = requests.get('https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json')
    releases = response.json()['releases']
    versions = []
    for release in releases:
        if release['channel'] in ['stable','beta']:
            versions.append((release['version'], release['archive'], release['release_date']))
    return versions


flutter_archive_url = "https://docs.flutter.dev/release/archive/"
flutter_download_url = "https://storage.googleapis.com/flutter_infra_release/releases/"

if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_NOFILE, (CONCURRENT_HTTP_CONNECTIONS*2, CONCURRENT_HTTP_CONNECTIONS*2))
    init_db()

    versions = get_flutter_versions()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=THREADS)
    print("Spawning", THREADS, "threads...")
    for e,version in enumerate(versions):
        while executor._work_queue.qsize() > THREADS*3: time.sleep(0.5)
        print(f"\x1b[31mDownloading version {e} out of {len(versions)}\x1b[0m")
        executor.map(lambda p: download_aar(p), [version], timeout=120)

    executor.shutdown()
