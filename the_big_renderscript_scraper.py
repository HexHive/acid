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

def download_aar():
    # get path of this script
    curdir =  os.path.dirname(os.path.realpath(__file__))
    temp_git = curdir+"/renderscript_temp"
    os.system(f"mkdir -p {temp_git}")
    temp_libs = tempfile.mkdtemp(prefix="acid_temp_libs_")

    try:
        if not os.path.exists("ground_truth_libs"): os.makedirs("ground_truth_libs")

        os.chdir(temp_git)
        print("Downloading sdk repo... this may take a while")
        subprocess.check_output(f"git clone {git_repo}", shell=True)

        poms = []

        os.chdir(temp_git+"/sdk")
        for file in files:
            print(file)
            commits = subprocess.check_output(f"git rev-list --all -- {file}", shell=True).decode().strip().split("\n")
            for commit in commits:
                print(f"Extracting {commit}:{file}")
                subprocess.check_output(f"git show {commit}:{file} > {temp_libs}/a", shell=True)
                shasum = subprocess.check_output(f"sha256sum {temp_libs}/a", shell=True).decode().strip().split(" ")[0]
                subprocess.check_output(f"mv {temp_libs}/a {curdir}/ground_truth_libs/{shasum}", shell=True)

                result = [{"name":os.path.basename(file), "hash":shasum}]

                pom = {}
                pom["url"] = git_repo
                pom["date"] = ":".join(subprocess.check_output(f"git show -s --format=%ci {commit}", shell=True).decode().strip().split(":")[:2])
                pom["artifact"] = "renderscript"
                pom["groupname"] = "google-prebuilt"
                pom["version"] = commit
                pom["name"] = "renderscript"
                pom["repository"] = git_repo
                pom["developer"] = "google"
                pom["source"] = "renderscript"

                poms += [(pom, result)]

        print(poms)

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

git_repo = "https://android.googlesource.com/platform/prebuilts/sdk"


files = [
"renderscript/lib/arm64/libRSSupport.so",
"renderscript/lib/arm64/libRSSupportIO.so",
"renderscript/lib/arm64/librsjni.so",
"renderscript/lib/arm64/librsjni_androidx.so",
]


if __name__ == "__main__":
    init_db()
    download_aar()
