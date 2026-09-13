import json
import os
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

TARGET = "https://toffeelive.com/en/watch/qnv835oBcqxnFHJBuQcB"

OUTPUT = "debug/toffee_requests.json"

SENSITIVE = {
     "bokachoda",
}


def clean_headers(headers):
    result = {}

    for key, value in headers.items():
        if key.lower() in SENSITIVE:
            result[key] = "[REDACTED]"
        else:
            result[key] = value

    return result


def main():

    os.makedirs("debug", exist_ok=True)

    requests_data = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        def on_request(request):

            try:
                headers = clean_headers(
                    request.headers
                )

                item = {
                    "time": datetime.now(
                        timezone.utc
                    ).isoformat(),

                    "method": request.method,

                    "resource_type":
                        request.resource_type,

                    "url": request.url,

                    "headers": headers,
                }

                requests_data.append(item)

                print(
                    f"[REQUEST] "
                    f"{request.method} "
                    f"{request.resource_type} "
                    f"{request.url}"
                )

            except Exception as e:

                print(
                    "[REQUEST ERROR]",
                    e
                )

        page.on(
            "request",
            on_request
        )

        print(
            "Opening:",
            TARGET
        )

        try:

            page.goto(
                TARGET,
                wait_until="domcontentloaded",
                timeout=60000
            )

        except Exception as e:

            print(
                "[PAGE ERROR]",
                e
            )

        # Allow API/playback requests to appear
        page.wait_for_timeout(20000)

        browser.close()

    # Detect possible M3U8 requests
    m3u8_requests = []

    for item in requests_data:

        url = item.get(
            "url",
            ""
        ).lower()

        if ".m3u8" in url:

            m3u8_requests.append(
                item
            )

    result = {
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "target": TARGET,

        "total_requests":
            len(requests_data),

        "m3u8_request_count":
            len(m3u8_requests),

        "m3u8_requests":
            m3u8_requests,

        "requests":
            requests_data,
    }

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)
    print(
        "Total requests:",
        len(requests_data)
    )
    print(
        "M3U8 requests:",
        len(m3u8_requests)
    )
    print(
        "Output:",
        OUTPUT
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
