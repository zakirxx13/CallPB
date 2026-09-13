import json
import os
import re
import requests
from datetime import datetime, timezone


CONTENT_API = "https://content-prod.services.toffeelive.com"
ENTITLEMENT_API = "https://entitlement-prod.services.toffeelive.com"

REGION = "BD"
CITY = "DK"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36"
)

session = requests.Session()

session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://toffeelive.com",
    "Referer": "https://toffeelive.com/",
})


# --------------------------------------------------
# Find M3U8 recursively inside JSON
# --------------------------------------------------

def find_m3u8(obj, path="root"):

    found = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            current_path = f"{path}.{key}"

            if isinstance(value, str):

                # Detect .m3u8 URL
                if ".m3u8" in value.lower():

                    found.append({
                        "path": current_path,
                        "url": value
                    })

            else:

                found.extend(
                    find_m3u8(
                        value,
                        current_path
                    )
                )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):

            current_path = f"{path}[{index}]"

            found.extend(
                find_m3u8(
                    value,
                    current_path
                )
            )

    return found


# --------------------------------------------------
# Find possible stream/playback fields
# --------------------------------------------------

def find_stream_fields(obj, path="root"):

    results = []

    interesting_keys = {
        "m3u8",
        "streamurl",
        "stream_url",
        "stream",
        "playbackurl",
        "playback_url",
        "url",
        "manifest",
        "manifesturl",
        "manifest_url",
        "hls",
        "hlsurl",
        "hls_url",
    }

    if isinstance(obj, dict):

        for key, value in obj.items():

            current_path = f"{path}.{key}"

            if key.lower() in interesting_keys:

                results.append({
                    "path": current_path,
                    "value": value
                })

            if isinstance(value, (dict, list)):

                results.extend(
                    find_stream_fields(
                        value,
                        current_path
                    )
                )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):

            results.extend(
                find_stream_fields(
                    value,
                    f"{path}[{index}]"
                )
            )

    return results


# --------------------------------------------------
# Fetch playback API
# --------------------------------------------------

def check_playback(content_id):

    url = (
        f"{ENTITLEMENT_API}"
        f"/toffee/{REGION}/{CITY}"
        f"/web/playback/{content_id}"
    )

    print()
    print("=" * 70)
    print("CONTENT ID:", content_id)
    print("PLAYBACK API:", url)
    print("=" * 70)

    try:

        response = session.get(
            url,
            timeout=30
        )

        print("HTTP STATUS:", response.status_code)

        # Don't process non-JSON responses
        content_type = response.headers.get(
            "content-type",
            ""
        )

        if "json" not in content_type.lower():

            print(
                "Response is not JSON."
            )

            return {
                "content_id": content_id,
                "status": response.status_code,
                "success": False,
                "m3u8": [],
                "stream_fields": [],
                "error": "Non-JSON response"
            }

        data = response.json()

        m3u8 = find_m3u8(data)

        stream_fields = find_stream_fields(
            data
        )

        print()
        print("M3U8 FOUND:", len(m3u8))

        for item in m3u8:

            print(
                "[M3U8]",
                item["path"]
            )

            print(
                item["url"]
            )

        print()
        print(
            "POSSIBLE STREAM FIELDS:",
            len(stream_fields)
        )

        for item in stream_fields:

            print(
                "[FIELD]",
                item["path"],
                "=",
                item["value"]
            )

        return {
            "content_id": content_id,
            "status": response.status_code,
            "success": response.ok,
            "m3u8": m3u8,
            "stream_fields": stream_fields,
        }

    except Exception as e:

        print(
            "[ERROR]",
            str(e)
        )

        return {
            "content_id": content_id,
            "success": False,
            "m3u8": [],
            "stream_fields": [],
            "error": str(e)
        }


# --------------------------------------------------
# Read channels.json
# --------------------------------------------------

def main():

    input_file = "data/channels.json"

    if not os.path.exists(input_file):

        print(
            f"File not found: {input_file}"
        )

        return

    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    channels = data.get(
        "channels",
        []
    )

    print(
        "TOTAL CHANNELS:",
        len(channels)
    )

    results = {
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total_channels": len(channels),

        "results": []
    }

    for number, channel in enumerate(
        channels,
        start=1
    ):

        content_id = channel.get(
            "id",
            ""
        )

        name = channel.get(
            "name",
            ""
        )

        if not content_id:

            continue

        print()
        print(
            f"[{number}/{len(channels)}]",
            name
        )

        result = check_playback(
            content_id
        )

        result["name"] = name

        results["results"].append(
            result
        )

    # --------------------------------------------------
    # Save result
    # --------------------------------------------------

    os.makedirs(
        "debug",
        exist_ok=True
    )

    output_file = (
        "debug/playback_check.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    found = 0

    for result in results["results"]:

        if result.get("m3u8"):

            found += 1

    print()
    print("=" * 70)
    print("CHECK COMPLETE")
    print("=" * 70)

    print(
        "Channels checked:",
        len(results["results"])
    )

    print(
        "Channels with M3U8:",
        found
    )

    print(
        "Result:",
        output_file
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
