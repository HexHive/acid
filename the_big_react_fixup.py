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
import subprocess
from datetime import datetime
from new_dload_apks import sha256sum
from the_big_maven_scraper import update_db_please_daddy, extract_libs_from_tmpdir, init_db

DB_PATH = "./the_base_of_datas.sqlite"

def download_aar():
    # get path of this script
    curdir =  os.path.dirname(os.path.realpath(__file__))
    temp_git = curdir+"/react_temp"
    os.system(f"mkdir -p {temp_git}")
    temp_libs = tempfile.mkdtemp(prefix="acid_temp_libs_")

    poms = []

    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()

    modules = cursor.execute("SELECT * FROM maven_truth_modules WHERE (artifact = (?) OR artifact = (?))", ("react-native", "react-android",)).fetchall()

    os.chdir(temp_git)
    subprocess.check_output(f"git clone {git_repo}", shell=True)
    subprocess.check_output(f"git clone {glog_repo}", shell=True)
    os.chdir(temp_git+"/react-native")

    for module in modules:
        id, artifact, groupname, name, url, version, repository, developer, date = module

        try:
            print(f"Checking out react native {version}")
            subprocess.check_output(f"git checkout v{version} 2>/dev/null", shell=True)

            glog_version, folly_version = "", ""
            if os.path.exists("packages/react-native/gradle/libs.versions.toml"):
                lines = open("packages/react-native/gradle/libs.versions.toml").read().split("\n")
                for line in lines:
                    if line.split("=")[0] == "glog":
                        glog_version = line.split("=")[1].strip().replace("\"", "")
                    if line.split("=")[0] == "folly":
                        folly_version = line.split("=")[1].strip().replace("\"", "")
            elif os.path.exists("ReactAndroid/gradle.properties"):
                lines = open("ReactAndroid/gradle.properties").read().split("\n")
                for line in lines:
                    if "GLOG_VERSION=" in line:
                        glog_version = line.split("=")[1].strip()
                    if "FOLLY_VERSION=" in line:
                        folly_version = line.split("=")[1].strip()
            elif os.path.exists("packages/react-native/ReactAndroid/gradle.properties"):
                lines = open("packages/react-native/ReactAndroid/gradle.properties").read().split("\n")
                for line in lines:
                    if "GLOG_VERSION=" in line:
                        glog_version = line.split("=")[1].strip()
                    if "FOLLY_VERSION=" in line:
                        folly_version = line.split("=")[1].strip()

            print(f"version {version}, glog: {glog_version}, folly: {folly_version}")

            if glog_version:
                pom = {}
                pom["url"] = glog_repo
                pom["date"] = ":".join(subprocess.check_output(f"cd ../glog; git show -s --format=%ci v{glog_version}", shell=True).decode().strip().split(":")[:2])
                pom["artifact"] = "glog"
                pom["groupname"] = "google-glog"
                pom["version"] = glog_version
                pom["name"] = "glog"
                pom["repository"] = glog_repo
                pom["developer"] = "google"
                pom["source"] = "react-glog"

                hashes = cursor.execute("SELECT * FROM maven_truth_hashes a JOIN maven_modules_hashes b ON a.id == b.hash_id WHERE module_id = (?)", (id,)).fetchall()
                result = []
                for h in hashes:
                    h_id, hash, relinked_hash, name, _, _ = h
                    if name in glog_names:
                        result += [{"name":name, "hash":hash}]

                print(result)
                if len(result):
                    poms += [(pom, result)]

            if folly_version:
                pom = {}
                pom["url"] = folly_repo
                pom["date"] = f"{folly_version.split('.')[0]}-{folly_version.split('.')[1]}-{folly_version.split('.')[2]} 00:00"
                pom["artifact"] = "folly"
                pom["groupname"] = "com.facebook.folly"
                pom["version"] = folly_version
                pom["name"] = "folly"
                pom["repository"] = folly_repo
                pom["developer"] = "facebook"
                pom["source"] = "react-folly"

                hashes = cursor.execute("SELECT * FROM maven_truth_hashes a JOIN maven_modules_hashes b ON a.id == b.hash_id WHERE module_id = (?)", (id,)).fetchall()
                result = []
                for h in hashes:
                    h_id, hash, relinked_hash, name, _, _ = h
                    if name in folly_names:
                        result += [{"name":name, "hash":hash}]

                print(result)
                if len(result):
                    poms += [(pom, result)]


        except Exception as e:
            print(e)
            continue
    try:
        os.chdir(curdir)
        for x in poms:
            pom, result = x
            try:
                print(pom)
                update_db_please_daddy(pom, result)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(e)
                os._exit(1)

        print("[+] done updating database")
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        # os._exit(1)
    finally:
        shutil.rmtree(temp_libs)
        shutil.rmtree(temp_git)


git_repo = "https://github.com/facebook/react-native"
glog_repo = "https://github.com/google/glog"
folly_repo = "https://github.com/facebook/folly"

glog_names = ["libglog.so"]
folly_names = ["libfolly.so", "libfolly_json.so", "libfolly_futures.so", "libfolly_runtime.so"] 

if __name__ == "__main__":
    init_db()
    download_aar()
