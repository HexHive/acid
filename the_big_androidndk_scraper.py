#!/usr/bin/env python3

import os
import hashlib
import requests
import tempfile
import shutil
from zipfile import ZipFile
from the_big_maven_scraper import update_db_please_daddy, init_db


def check_file_exists(url):
    """Check if a file exists on the server by sending a HEAD request"""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking if {url} exists: {e}")
        return False


def download_and_process_ndk(version, output_dir):
    """Download NDK zip for a specific version and extract libc++_shared.so files"""

    # Check if the file exists before attempting download
    latest_mtime = "0"


    url = f"https://dl.google.com/android/repository/android-ndk-{version}-linux.zip"
    if not check_file_exists(url):
        url = f"https://dl.google.com/android/repository/android-ndk-{version}-linux-x86_64.zip"
        if not check_file_exists(url):
            print(f"Version {version} not available at {url}")
            return []

    print(f"Downloading {url}")
    try:
        # Stream the download to avoid loading entire file into memory
        response = requests.get(url, stream=True)
        if response.status_code != 200:
                print(f"Failed to download {url}, status code: {response.status_code}")
                return []

        # Create a temporary file for the zip
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Download the file
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            print(f"Total size: {total_size / (1024*1024):.2f} MB")

            for chunk in response.iter_content(chunk_size=(1024 * 1024)):
                if chunk:
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    # Print progress every 10%
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        if percent % 10 == 0:
                            print(f"Downloaded {percent}%")

            temp_file_path = temp_file.name

        # Process the zip file
        extracted_files = []
        print(f"Processing zip file for version {version}")

        with ZipFile(temp_file_path, 'r') as zip_file:
            # Find all library files
            lib_files = [f for f in zip_file.namelist() if ("arm64" in f or "aarch64" in f) and f.endswith('.so')]
            print(f"Found {len(lib_files)} library files")

            # Extract each file and rename based on SHA256
            for lib_file in lib_files:
                # Extract to temp directory
                temp_dir = tempfile.mkdtemp()
                extracted_path = zip_file.extract(lib_file, temp_dir)

                mtime = zip_file.getinfo(lib_file).date_time
                year, month, day, hour, minute, second = mtime
                # transform into YYYY-MM-DD HH:MM format
                mtime = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"

                latest_mtime = max(latest_mtime, mtime)


                # Calculate SHA256
                with open(extracted_path, 'rb') as f:
                    file_content = f.read()
                    sha256_hash = hashlib.sha256(file_content).hexdigest()

                # Save file with SHA256 as name
                output_path = os.path.join(output_dir, sha256_hash)
                shutil.move(extracted_path, output_path)
                print(f"Saved {lib_file} as {sha256_hash}")

                # get basename of lib_file
                lib_file = os.path.basename(lib_file)
                extracted_files.append({"name": lib_file, "hash": sha256_hash})

                # Clean up temp directory
                shutil.rmtree(temp_dir)

        # Clean up temp zip file
        os.unlink(temp_file_path)
        return (url, extracted_files, latest_mtime)

    except Exception as e:
        print(f"Error processing {version}: {e}")
        return []



def main():
    # Create output directory
    curdir =  os.path.dirname(os.path.realpath(__file__))
    output_dir = "ground_truth_libs"
    os.makedirs(output_dir, exist_ok=True)

    # Generate all version combinations
    versions = []

    # Add major versions (r8 to r30)
    for i in range(8, 31):
        versions.append(f"r{i}")

    # Add lettered versions (r8a to r30e)
    for i in range(8, 31):
        for letter in 'abcde':
            versions.append(f"r{i}{letter}")

    # Track results
    results = {}
    poms = []


    # Process each version
    for version in versions:
        print(f"\n===== Processing NDK version {version} =====")
        res = download_and_process_ndk(version, output_dir)
        if not res:
            continue
        url, extracted, date = res
        if extracted:
            results[version] = extracted

        pom = {}
        pom["url"] = url
        pom["date"] = date
        pom["artifact"] = "android-ndk"
        pom["groupname"] = "com.google.ndk"
        pom["version"] = version
        pom["name"] = "android-ndk"
        pom["repository"] = url
        pom["developer"] = "google"
        pom["source"] = "android-ndk"

        print(pom)
        print(results[version])
        poms += [(pom, results[version])]

    os.chdir(curdir)
    for x in poms:
        pom, result = x
        try:
            update_db_please_daddy(pom, result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
            os._exit(1)

    print("[+] done updating database")

    # Print summary
    print("\n===== Summary =====")
    print(f"Processed {len(results)} NDK versions")
    print(f"Total extracted libc++_shared.so files: { sum(len(files) for files in results.values())}")


if __name__ == "__main__":
    init_db()
    main()
