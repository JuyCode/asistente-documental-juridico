import time
from playwright.sync_api import sync_playwright

URL = "https://asistente-documental-juridico-azs3hvkxwkxytpezrp4ku3.streamlit.app/~/+/"

def wait_until(cond, timeout=60, interval=3):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if cond():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    logs = []
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text[:160]}"))

    page.goto(URL, wait_until="domcontentloaded", timeout=90000)
    ok = wait_until(lambda: len(page.inner_text("body")) > 80, timeout=90)
    print("1) TEXTO PRESENTE:", ok)
    print("2) TITLE:", page.title())

    body = page.inner_text("body")
    print("3) BODY[:2200]:")
    print(body[:2200])

    print("4) uploaders:", page.locator('input[type="file"]').count())
    print("5) chat textareas:", page.locator("textarea").count())

    f = None
    for fr in page.frames:
        if "~/+/" in fr.url:
            f = fr
            break
    if f is None and page.frames:
        f = page.main_frame
    if f is not None:
        fb = f.inner_text("body")
        print("6) FRAME BODY[:2200]:")
        print(fb[:2200])
        print("7) frame uploaders:", f.locator('input[type="file"]').count())

    print("8) logs:")
    for l in logs[-20:]:
        print("   ", l)
    browser.close()