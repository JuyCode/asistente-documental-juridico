import time
import sys

from playwright.sync_api import sync_playwright

URL = "https://asistente-documental-juridico-azs3hvkxwkxytpezrp4ku3.streamlit.app/~/+/"
OUT = r"C:\Users\user\AppData\Local\Temp\opencode\verify_result.txt"
RESULT = []

def out(msg):
    RESULT.append(str(msg))

def wait_until(cond, timeout=120, interval=3):
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
    console_errors = []
    page.on("console", lambda m: console_errors.append(f"[{m.type}] {m.text[:180]}") if m.type == "error" else None)

    page.goto(URL, wait_until="domcontentloaded", timeout=90000)

    ok = wait_until(lambda: len(page.inner_text("body")) > 80, timeout=120)
    out(f"[1] App cargada y renderizada: {ok}")
    if not ok:
        out("BODY: " + page.inner_text("body")[:800])

    time.sleep(4)
    body = page.inner_text("body")
    out("[2] TEXTO VISIBLE (completo):")
    out("==========")
    out(body)
    out("==========")

    out(f"[3] Uploader de archivos para VISITANTE: {page.locator('input[type=file]').count()} (debe ser 0)")

    chat = page.locator('textarea[data-testid="stChatInputTextArea"], textarea[data-testid="chat_input_value_id"], textarea[placeholder]')
    n_chat = chat.count()
    ph = chat.first.get_attribute("placeholder") if n_chat else ""
    enabled = chat.first.is_enabled() if n_chat else False
    out(f"[4] Chat input: {n_chat} | placeholder: '{ph}' | habilitado: {enabled}")

    exp = page.get_by_text("Acceder como administrador")
    out(f"[5] Existe panel admin 'Acceder como administrador': {exp.count() > 0}")
    if exp.count():
        exp.first.click()
        time.sleep(1)
        pwd = page.locator('input[type="password"]')
        btn = page.get_by_role("button", name="Ingresar")
        out(f"[5b] Campo clave: {pwd.count()} | botón Ingresar: {btn.count()}")
        if pwd.count() and btn.count():
            pwd.first.fill("clave_erronea_xyz")
            btn.first.click()
            time.sleep(2)
            b2 = page.inner_text("body")
            out(f"[6] Clave INCORRECTA -> muestra 'Clave incorrecta.': {'Clave incorrecta.' in b2}")
            uploaders_after = page.locator('input[type="file"]').count()
            out(f"[6b] Uploaders tras clave incorrecta: {uploaders_after} (debe seguir 0)")

    if n_chat and enabled:
        q = "Define el servicio del contrato."
        chat.first.fill(q)
        chat.first.press("Enter")
        time.sleep(6)
        spinner = page.locator('[data-testid="stStatusWidget"]')
        wait_until(lambda: spinner.count() == 0, timeout=150)
        time.sleep(3)
        chat_text = page.inner_text("body")
        out("[7] CONVERSACIÓN COMPLETA:")
        out("==========")
        out(chat_text)
        out("==========")
        out(f"[8] Firma anti-alucinación presente: {'No dispongo de esa información' in chat_text}")

    out("[9] Errores de consola:")
    for e in console_errors[-10:]:
        out("    " + e)

    browser.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(RESULT))
print("OK")