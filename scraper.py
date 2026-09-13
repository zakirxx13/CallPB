#!/usr/bin/env python3

import json
import os
import hashlib
from datetime import datetime, timezone

import requests


class ToffeeScraper:

    CONTENT_API = "https://content-prod.services.toffeelive.com"
    ENTITLEMENT_API = "https://entitlement-prod.services.toffeelive.com"

    REGION = "BD"
    CITY = "DK"

    RAIL_IDS = [
        "cceb01a3ecb01516539b0adad38c1400",
        "08d90cecf964eb9a5f6be2e1887066fd",
        "55fdb2bedaca2de399b470fb0ce14117",
        "911e8f640af3a8892b628714d4acc133",
        "84a2451df95d2eb3d2b0d09c5fc34fb1",
        "9988b22058e87ba742a8d734e640e759",
        "be7d42854f019db42fbc22153674b888",
        "36eff4e5ed817e63c4a0859a0e11f1d5",
        "cb7ea308e7742680ea8df1aae153bc9b",
    ]

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/128.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://toffeelive.com",
            "Referer": "https://toffeelive.com/",
        })

        self.debug = {
            "started_at": self.now(),
            "rails": [],
            "playback": [],
            "errors": [],
        }

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def safe_text(value):
        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        return str(value).strip()

    # --------------------------------------------------
    # Rail API
    # --------------------------------------------------

    def fetch_rail(self, rail_id):

        url = (
            f"{self.CONTENT_API}"
            f"/toffee/{self.REGION}/{self.CITY}"
            f"/web/rail/generic/editorial-dynamic/{rail_id}"
        )

        print(f"[RAIL] {rail_id}")

        try:

            response = self.session.get(
                url,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            self.debug["rails"].append({
                "rail_id": rail_id,
                "status": response.status_code,
                "success": True,
            })

            return data

        except Exception as exc:

            error = {
                "type": "rail",
                "rail_id": rail_id,
                "error": str(exc),
            }

            self.debug["errors"].append(error)

            self.debug["rails"].append({
                "rail_id": rail_id,
                "success": False,
                "error": str(exc),
            })

            print(f"[ERROR] Rail failed: {exc}")

            return None

    # --------------------------------------------------
    # Find objects recursively
    # --------------------------------------------------

    def find_content_objects(self, obj):

        found = []

        if isinstance(obj, dict):

            # Common content object indicators
            if (
                "id" in obj
                and (
                    "title" in obj
                    or "name" in obj
                    or "subType" in obj
                    or "media" in obj
                    or "images" in obj
                )
            ):
                found.append(obj)

            for value in obj.values():
                found.extend(
                    self.find_content_objects(value)
                )

        elif isinstance(obj, list):

            for item in obj:
                found.extend(
                    self.find_content_objects(item)
                )

        return found

    # --------------------------------------------------
    # Logo extraction
    # --------------------------------------------------

    def extract_logo(self, item):

        images = item.get("images", [])

        if not isinstance(images, list):
            return ""

        candidates = []

        for image in images:

            if not isinstance(image, dict):
                continue

            path = (
                image.get("path")
                or image.get("url")
                or image.get("src")
                or ""
            )

            if path:
                candidates.append(
                    self.safe_text(path)
                )

        if not candidates:
            return ""

        # Prefer logo-like images
        for image in candidates:

            lower = image.lower()

            if (
                "logo" in lower
                or "channel" in lower
            ):
                return image

        return candidates[0]

    # --------------------------------------------------
    # Channel parser
    # --------------------------------------------------

    def parse_channel(self, item, rail_id):

        content_id = self.safe_text(
            item.get("id")
        )

        if not content_id:
            return None

        title = (
            item.get("title")
            or item.get("name")
            or item.get("displayName")
            or ""
        )

        title = self.safe_text(title)

        if not title:
            return None

        subtype = self.safe_text(
            item.get("subType")
        )

        category = (
            item.get("catogory")
            or item.get("category")
            or item.get("categoryName")
            or ""
        )

        category = self.safe_text(category)

        external_id = self.safe_text(
            item.get("externalId")
        )

        logo = self.extract_logo(item)

        media_ids = []

        media = item.get("media", [])

        if isinstance(media, list):

            for media_item in media:

                if not isinstance(media_item, dict):
                    continue

                media_id = (
                    media_item.get("mediaId")
                    or media_item.get("id")
                )

                if media_id:
                    media_ids.append(
                        self.safe_text(media_id)
                    )

        channel = {
            "id": content_id,
            "name": title,
            "category": category,
            "subType": subtype,
            "externalId": external_id,
            "logo": logo,
            "mediaIds": list(dict.fromkeys(media_ids)),
            "railId": rail_id,
        }

        return channel

    # --------------------------------------------------
    # Playback API
    # --------------------------------------------------

    def fetch_playback(self, content_id):

        url = (
            f"{self.ENTITLEMENT_API}"
            f"/toffee/{self.REGION}/{self.CITY}"
            f"/web/playback/{content_id}"
        )

        print(f"[PLAYBACK] {content_id}")

        try:

            response = self.session.get(
                url,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            self.debug["playback"].append({
                "content_id": content_id,
                "status": response.status_code,
                "success": True,
            })

            return data

        except Exception as exc:

            self.debug["playback"].append({
                "content_id": content_id,
                "success": False,
                "error": str(exc),
            })

            return None

    # --------------------------------------------------
    # Scrape
    # --------------------------------------------------

    def scrape(self):

        channels = {}

        for rail_id in self.RAIL_IDS:

            rail_data = self.fetch_rail(
                rail_id
            )

            if not rail_data:
                continue

            objects = self.find_content_objects(
                rail_data
            )

            print(
                f"[INFO] Found {len(objects)} "
                f"objects in rail"
            )

            for item in objects:

                channel = self.parse_channel(
                    item,
                    rail_id
                )

                if not channel:
                    continue

                channel_id = channel["id"]

                # Deduplicate by content ID
                if channel_id not in channels:

                    channels[channel_id] = channel

        channel_list = list(
            channels.values()
        )

        channel_list.sort(
            key=lambda x: x["name"].lower()
        )

        print(
            f"[DONE] Unique channels: "
            f"{len(channel_list)}"
        )

        return channel_list

    # --------------------------------------------------
    # Save JSON
    # --------------------------------------------------

    def save_json(self, channels):

        os.makedirs("data", exist_ok=True)

        output = {
            "generatedAt": self.now(),
            "region": self.REGION,
            "city": self.CITY,
            "totalChannels": len(channels),
            "channels": channels,
        }

        path = "data/channels.json"

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                output,
                file,
                indent=2,
                ensure_ascii=False
            )

        print(f"[SAVE] {path}")

        return output

    # --------------------------------------------------
    # Save M3U
    # --------------------------------------------------

    def save_m3u(self, channels):

        os.makedirs("data", exist_ok=True)

        path = "data/toffeelive.m3u"

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write("#EXTM3U\n")

            for channel in channels:

                name = channel["name"]
                logo = channel["logo"]
                category = channel["category"]

                # Metadata-only playlist entry.
                # No protected stream URL is fabricated.
                file.write(
                    f'#EXTINF:-1 '
                    f'tvg-id="{channel["id"]}" '
                    f'tvg-logo="{logo}" '
                    f'group-title="{category}",'
                    f'{name}\n'
                )

                file.write(
                    "# Stream URL supplied by the "
                    "authorized playback system\n"
                )

        print(f"[SAVE] {path}")

    # --------------------------------------------------
    # Save debug
    # --------------------------------------------------

    def save_debug(self):

        os.makedirs(
            "debug",
            exist_ok=True
        )

        self.debug["finished_at"] = self.now()

        path = "debug/latest.json"

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.debug,
                file,
                indent=2,
                ensure_ascii=False
            )

        print(f"[SAVE] {path}")

    # --------------------------------------------------
    # Save raw rail data
    # --------------------------------------------------

    def save_raw(self, rail_results):

        os.makedirs(
            "debug/raw",
            exist_ok=True
        )

        for rail_id, data in rail_results:

            if data is None:
                continue

            path = (
                f"debug/raw/{rail_id}.json"
            )

            with open(
                path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=2,
                    ensure_ascii=False
                )

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def run(self):

        print("=" * 60)
        print("TOFFEE LIVE SCRAPER")
        print("=" * 60)

        channels = self.scrape()

        self.save_json(channels)

        self.save_m3u(channels)

        self.save_debug()

        print("=" * 60)
        print(
            f"TOTAL CHANNELS: {len(channels)}"
        )
        print("=" * 60)


def main():

    scraper = ToffeeScraper()

    try:
        scraper.run()

    except Exception as exc:

        os.makedirs(
            "debug",
            exist_ok=True
        )

        error_path = (
            "debug/fatal_error.txt"
        )

        with open(
            error_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                f"Time: {datetime.now(timezone.utc)}\n"
            )

            file.write(
                f"Error: {exc}\n"
            )

        raise


if __name__ == "__main__":
    main()
