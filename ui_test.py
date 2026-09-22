# Test de UI con Streamlit AppTest: arranca la app y simula una pregunta real.
import sys
sys.path.insert(0, r"C:\Users\user\Desktop\prueba1")

from streamlit.testing.v1 import AppTest

at = AppTest.from_file(r"C:\Users\user\Desktop\prueba1\app.py", default_timeout=120)
at.run()
print(f"Excepciones al arrancar: {len(at.exception)}")
for e in at.exception:
    print("  EXC:", e)

# Modo cliente/visitante: NO debe haber uploader de PDFs
print(f"File uploaders visibles para visitante: {len(at.file_uploader)}")
print(f"Mensajes de chat renderizados: {len(at.chat_message)}")
print(f"Errores en sidebar: {len(at.error)}")
for er in at.error:
    print("  ERROR:", er.value)


# Simulamos acceso admin con la clave correcta (está en .env)
def type_admin(at):
    if at.text_input and any("Clave de administraci" in lbl for lbl in [t.label for t in at.text_input if hasattr(t, "label")]):
        field = [t for t in at.text_input if hasattr(t, "label") and "Clave de administraci" in t.label][0]
        field.set_value("estudio2026")
        return True
    return False

buttons = list(at.button)
if buttons:
    ingresar = [b for b in buttons if "Ingresar" in str(getattr(b, "label", ""))]
    if ingresar:
        at.text_input[0].set_value("estudio2026")
        ingresar[0].click().run()
        print(f"Admin: excepciones={len(at.exception)} | uploaders ahora={len(at.file_uploader)}")


# Simulamos una consulta en el chat
if at.chat_input:
    at.chat_input[0].set_value("¿Cuál es el canon mensual del contrato?").run()
    print(f"Excepciones tras pregunta: {len(at.exception)}")
    for e in at.exception:
        print("  EXC:", e)
    print(f"Mensajes tras pregunta: {len(at.chat_message)}")
    print(f"Expanders (fuentes) renderizados: {len(at.expander)}")
    print("UI TEST OK")
else:
    print("chat_input no encontrado (revisar disabled/placeholder)")
    print("UI TEST PARCIAL")