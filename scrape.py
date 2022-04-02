#!/bin/env python3

import re
import os
import mimetypes
import uuid
import requests
import argparse
from concurrent.futures import ThreadPoolExecutor

KNOCKOUT_API_THREAD_URL = "https://api.knockout.chat/thread/{thread_id}/{page_number}"

def get_thread(thread_id, page_number=1):
    response = requests.get(KNOCKOUT_API_THREAD_URL.format(thread_id=thread_id, page_number=page_number))
    response.raise_for_status()

    return response.json()

def get_posts(thread_id):
    thread = get_thread(thread_id)
    page_count = thread["lastPost"]["page"]

    for page_number in range(2, page_count):
        yield from thread["posts"]
        thread = get_thread(thread_id, page_number)

def get_urls(thread_id, tags=["img"]):
    for post in get_posts(thread_id):
        # Remove all quoted posts
        text = re.sub(r"\[quote.*?\].*?\[\/quote\]", "", post["content"])

        for tag in tags:
            finds = re.finditer(fr"\[{tag}\](.*?)\[\/{tag}\]", text, re.IGNORECASE)
            finds = filter(lambda match: match is not None, finds)
            finds = map(lambda match: match[1], finds)
            yield from finds

def download_file(url, base_folder):
    response = requests.get(url, stream=True)
    response.raise_for_status()

    filename = uuid.uuid4()
    extension = mimetypes.guess_extension(response.headers["content-type"])

    os.makedirs(base_folder, exist_ok=True)

    with open(os.path.join(base_folder, f"{filename}{extension}"), "wb") as file:
        for chunk in response.iter_content(1024):
            file.write(chunk)

def main():
    parser = argparse.ArgumentParser(
        description="Download all images and videos from a Knockout thread"
    )
    parser.add_argument("thread_id", type=int, help="Thread ID from which the files will be downloaded")
    parser.add_argument("--folder", "-f", type=str, default="files/", help="Output folder")
    parser.add_argument("--tags", "-t", type=str, default=["img", "video"], nargs="+", help="Tags which will be searched for urls")

    args = parser.parse_args()
    urls = get_urls(args.thread_id, args.tags)

    with ThreadPoolExecutor() as pool:
        for url in urls:
            print(f"Downloading {url}")
            pool.submit(download_file, url, args.folder)

if __name__ == "__main__":
    main()