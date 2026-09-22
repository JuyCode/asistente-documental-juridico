# Test de UI con Streamlit AppTest: arranca la app y simula una pregunta real.
import sys
sys.path.insert(0, r"C:\Users\user\Desktop\prueba1")

from streamlit.testing.v1 import AppTest

at = AppTest.from_file(r"C:\Users\user\Desktop\prueba1\app.py", default_timeout=120)
at.run()
print(f"Excepciones al arrancar: {len(at.exception)}")
for e in at.exception:
    print("  EXC:", e)

# ¿Botón de indexar visible? (app ya tiene índice local con test_contrato.pdf)
print(f"Mensajes de chat renderizados: {len(at.chat_message)}")
print(f"Errores en sidebar: {len(at.error)}")
for er in at.error:
    print("  ERROR:", er.value)

# Simulamos una consulta en el chat
if at.chat_input:
    at.chat_input[0].set_value("¿Cuál es el canon mensual del contrato?").run()
    print(f"Excepciones tras pregunta: {len(at.exception)}")
    for e in at.exception:
        print("  EXC:", e)
    print(f"Mensajes tras pregunta: {len(at.chat_message)}")
    def _safe_str(m):
        for attr in ("value", "text", "markdown", "content"):
            v = getattr(m, attr, None)
            if v is not None:
                return v
        return repr(m)
    for i, m in enumerate(at.chat_message):
        label = getattr(m, "name", None) or getattr(m, "role", None) or f"msg{i}"
        content = str(_safe_str(m))
        print(f"  [{label}] {content[:140]!r}")
    print(f"Expanders (fuentes) renderizados: {len(at.expander)}")
    print("UI TEST OK")
else:
    print("chat_input no encontrado (revisar disabled/placeholder)")
    print("UI TEST PARCIAL")