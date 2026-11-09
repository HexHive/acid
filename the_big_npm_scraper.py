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
from datetime import datetime
from new_dload_apks import sha256sum
from the_big_maven_scraper import update_db_please_daddy, extract_libs_from_tmpdir, init_db


DB_PATH = "./the_base_of_datas.sqlite"
THREADS = 1
CONCURRENT_HTTP_CONNECTIONS = 100000


def dload_libs_in_temp_dir(version, temp_libs):
    url = react_npm_url + version + ".tgz"
    print(f"[..] downloading {url}")
    tar_file = requests.get(url).content
    with tarfile.open(fileobj=io.BytesIO(tar_file), mode='r') as tar:
        for member in tar.getmembers():
            if member.name.endswith(".aar"):
                zip_file_like = io.BytesIO(tar.extractfile(member).read())
                with zipfile.ZipFile(zip_file_like, 'r') as zipf:
                    for zip_member in zipf.namelist():
                        if zip_member.startswith("jni/arm64") and not zip_member.endswith("/"):
                            target_path = os.path.join(temp_libs,os.path.basename(zip_member))
                            with zipf.open(zip_member) as file_data, open(target_path, 'wb') as output_file:
                                output_file.write(file_data.read())
                            print(f'Extracted file from zip: {zip_member} to {target_path}')

def download_aar(version):
    temp_libs = tempfile.mkdtemp(prefix="acid_temp_libs_")
    try:
        if not os.path.exists("ground_truth_libs"): os.makedirs("ground_truth_libs")

        dload_libs_in_temp_dir(version, temp_libs)

        result = extract_libs_from_tmpdir(temp_libs)

        if not len(result): return []

        pom = {}
        pom["url"] = react_npm_url + version + ".tgz"
        pom["date"] = datetime.strptime(dates[version], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M")
        pom["artifact"] = "react-native"
        pom["groupname"] = "com.facebook.react"
        pom["version"] = version
        pom["name"] = "react native"
        pom["repository"] = "https://github.com/facebook/react-native"
        pom["developer"] = "facebook"
        pom["source"] = "npm"

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
        print(e)
        import traceback
        traceback.print_exc()
        # os._exit(1)
    finally:
        shutil.rmtree(temp_libs)

react_native_npm_versions = ['0.20.0', '0.21.0-rc', '0.21.0', '0.22.0-rc', '0.22.0-rc3', '0.22.0-rc4', '0.22.0-rc5', '0.22.0', '0.22.1', '0.22.2', '0.23.0-rc1', '0.23.0-rc3', '0.23.0-rc4', '0.23.0', '0.23.1', '0.24.0-rc', '0.24.0-rc1', '0.24.0-rc2', '0.24.0-rc3', '0.24.0-rc4', '0.24.0-rc5', '0.24.0', '0.24.1', '0.25.0-rc', '0.25.1', '0.26.0-rc', '0.26.0', '0.26.1', '0.26.2', '0.26.3', '0.27.0-rc', '0.27.0-rc1', '0.27.0-rc2', '0.27.0-rc3', '0.27.0', '0.27.1', '0.27.2', '0.28.0-rc.0', '0.28.0', '0.29.0-rc.0', '0.29.0-rc.1', '0.29.0-rc.2', '0.29.0-rc.3', '0.29.0', '0.29.1', '0.29.2', '0.30.0-rc.0', '0.30.0', '0.31.0-rc.0', '0.31.0-rc.1', '0.31.0', '0.32.0-rc.0', '0.32.0', '0.32.1', '0.33.0-rc.0', '0.33.0-rc.1', '0.33.0', '0.33.1', '0.34.0-rc.0', '0.34.0', '0.34.1', '0.35.0-rc.0', '0.35.0', '0.36.0-rc.0', '0.36.0-rc.1', '0.36.0', '0.36.1', '0.37.0-rc.0', '0.37.0-rc.2', '0.37.0-rc.3', '0.37.0-rc.4', '0.37.0', '0.38.0-rc.0', '0.38.0-rc.1', '0.38.0', '0.38.1', '0.39.0-rc.0', '0.39.0', '0.39.1', '0.39.2', '0.40.0-rc.0', '0.40.0-rc.1', '0.40.0-rc.2', '0.40.0', '0.41.0-rc.0', '0.41.0-rc.1', '0.41.0', '0.41.1', '0.41.2', '0.42.0-rc.0', '0.42.0-rc.1', '0.42.0-rc.2', '0.42.0-rc.3', '0.42.0', '0.42.2', '0.42.3', '0.43.0-rc.0', '0.43.0-rc.1', '0.43.0-rc.2', '0.43.0-rc.3', '0.43.0-rc.4', '0.43.0', '0.43.1', '0.43.2', '0.43.3', '0.43.4', '0.44.0-rc.0', '0.44.0', '0.44.1', '0.44.2', '0.44.3', '0.45.0-rc.0', '0.45.0-rc.1', '0.45.0-rc.2', '0.45.0-rc.3', '0.45.0', '0.45.1', '0.46.0-rc.0', '0.46.0-rc.1', '0.46.0-rc.2', '0.46.0', '0.46.1', '0.46.2', '0.46.3', '0.46.4', '0.47.0-rc.0', '0.47.0-rc.1', '0.47.0-rc.2', '0.47.0-rc.3', '0.47.0-rc.4', '0.47.0-rc.5', '0.47.0', '0.47.1', '0.47.2', '0.48.0-rc.0', '0.48.0-rc.1', '0.48.0', '0.48.1', '0.48.2', '0.48.3', '0.48.4', '0.49.0-rc.2', '0.49.0-rc.4', '0.49.0-rc.5', '0.49.0-rc.6', '0.49.0', '0.49.1', '0.49.2', '0.49.3', '0.49.5', '0.50.0-rc.0', '0.50.0-rc.1', '0.50.0-rc.2', '0.50.0', '0.50.1', '0.50.2', '0.50.3', '0.50.4', '0.51.0-rc.2', '0.51.0-rc.3', '0.51.0', '0.51.1', '0.52.0-rc.0', '0.52.0', '0.52.1', '0.52.2', '0.52.3', '0.53.0-rc.0', '0.53.0', '0.53.2', '0.53.3', '0.54.0-rc.0', '0.54.0-rc.2', '0.54.0-rc.3', '0.54.0-rc.4', '0.54.0', '0.54.1', '0.54.2', '0.54.3', '0.54.4', '0.55.0-rc.0', '0.55.0-rc.1', '0.55.0-rc.2', '0.55.0', '0.55.1', '0.55.2', '0.55.3', '0.55.4', '0.56.0-rc', '0.56.0-rc.1', '0.56.0-rc.2', '0.56.0-rc.3', '0.56.0-rc.4', '0.56.0-rc.5', '0.56.0', '0.56.1', '0.57.0-rc.0', '0.57.0-rc.1', '0.57.0-rc.2', '0.57.0-rc.3', '0.57.0-rc.4', '0.57.0', '0.57.1', '0.57.2', '0.57.3', '0.57.4', '0.57.5', '0.57.6', '0.57.7', '0.57.8', '0.58.0-rc.0', '0.58.0-rc.1', '0.58.0-rc.2', '0.58.0-rc.3', '0.58.0', '0.58.1', '0.58.2', '0.58.3', '0.58.4', '0.58.5', '0.58.6', '0.59.0-rc.0', '0.59.0-rc.1', '0.59.0-rc.2', '0.59.0-rc.3', '0.59.0', '0.59.1', '0.59.2', '0.59.3', '0.59.4', '0.59.5', '0.59.6', '0.59.7', '0.59.8', '0.59.9', '0.59.10', '0.60.0-rc.0', '0.60.0-rc.1', '0.60.0-rc.2', '0.60.0-rc.3', '0.60.0', '0.60.1', '0.60.2', '0.60.3', '0.60.4', '0.60.5', '0.60.6', '0.61.0-rc.0', '0.61.0-rc.2', '0.61.0-rc.3', '0.61.0', '0.61.1', '0.61.2', '0.61.3', '0.61.4', '0.61.5', '0.62.0-rc.0', '0.62.0-rc.1', '0.62.0-rc.2', '0.62.0-rc.3', '0.62.0-rc.4', '0.62.0-rc.5', '0.62.0', '0.62.1', '0.62.2', '0.62.3', '0.63.0-rc.0', '0.63.0-rc.1', '0.63.0', '0.63.1', '0.63.2', '0.63.3', '0.63.4', '0.63.5', '0.64.0-rc.0', '0.64.0-rc.1', '0.64.0-rc.2', '0.64.0-rc.3', '0.64.0-rc.4', '0.64.0', '0.64.1', '0.64.2', '0.64.3', '0.64.4', '0.65.0-rc.0', '0.65.0-rc.1', '0.65.0-rc.2', '0.65.0-rc.3', '0.65.0-rc.4', '0.65.0', '0.65.1', '0.65.2', '0.65.3', '0.66.0-rc.0', '0.66.0-rc.1', '0.66.0-rc.2', '0.66.0-rc.3', '0.66.0-rc.4', '0.66.0', '0.66.1', '0.66.2', '0.66.3', '0.66.4', '0.66.5', '0.67.0-rc.0', '0.67.0-rc.1', '0.67.0-rc.2', '0.67.0-rc.3', '0.67.0-rc.4', '0.67.0-rc.5', '0.67.0-rc.6', '0.67.0', '0.67.1', '0.67.2', '0.67.3', '0.67.4', '0.67.5', '0.68.0-rc.0', '0.68.0-rc.1', '0.68.0-rc.2', '0.68.0-rc.3', '0.68.0-rc.4', '0.68.0', '0.68.1', '0.68.2', '0.68.3', '0.68.4', '0.68.5', '0.68.6', '0.68.7', '0.69.0-rc.0', '0.69.0-rc.1', '0.69.0-rc.2', '0.69.0-rc.3', '0.69.0-rc.4', '0.69.0-rc.5', '0.69.0-rc.6', '0.69.0', '0.69.1', '0.69.2', '0.69.3', '0.69.4', '0.69.5', '0.69.6', '0.69.7', '0.69.8', '0.69.9', '0.69.10', '0.69.11', '0.69.12', '0.70.0-rc.0', '0.70.0-rc.1', '0.70.0-rc.2', '0.70.0-rc.3', '0.70.0-rc.4', '0.70.0', '0.70.1', '0.70.2', '0.70.3', '0.70.4', '0.70.5', '0.70.6', '0.70.7', '0.70.8', '0.70.9', '0.70.10', '0.70.11', '0.70.12', '0.70.13', '0.70.14', '0.70.15', '0.71.0-rc.0', '0.71.0-rc.1', '0.71.0-rc.2', '0.71.0-rc.3', '0.71.0-rc.4', '0.71.0-rc.5', '0.71.0-rc.6', '0.71.0',]
react_npm_url = "https://registry.npmjs.org/react-native/-/react-native-"
dates = json.loads(requests.get("https://registry.npmjs.org/react-native/").text)["time"]

if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_NOFILE, (CONCURRENT_HTTP_CONNECTIONS*2, CONCURRENT_HTTP_CONNECTIONS*2))
    init_db()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=THREADS)
    print("Spawning", THREADS, "threads...")
    for e,npm_version in enumerate(react_native_npm_versions):
        while executor._work_queue.qsize() > THREADS*30: time.sleep(0.5)
        print(f"\x1b[31mDownloading react-native version {e} out of {len(react_native_npm_versions)}\x1b[0m")
        executor.map(lambda p: download_aar(p), [npm_version], timeout=120)

    executor.shutdown()
