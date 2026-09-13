from playwright.sync_api import sync_playwright

TARGET = "https://toffeelive.com/en/watch/qnv835oBcqxnFHJBuQcB"

SENSITIVE = {
    "cookie",
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "x-device-key",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    def inspect_request(request):
        print("\n" + "=" * 80)
        print("METHOD :", request.method)
        print("TYPE   :", request.resource_type)
        print("URL    :", request.url)

        print("\nHEADERS:")
        for key, value in request.headers.items():
            if key.lower() in SENSITIVE:
                print(f"{key}: [REDACTED]")
            else:
                print(f"{key}: {value}")

    page.on("request", inspect_request)

    print("Opening:", TARGET)

    page.goto(
        TARGET,
        wait_until="domcontentloaded",
        timeout=60000
    )

    # Give the page time to make its normal requests
    page.wait_for_timeout(15000)

    print("\nDone.")

    browser.close()
