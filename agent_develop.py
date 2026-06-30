from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.tools import PythonREPLTool
import os
import re
import json
import shutil
import subprocess
import logging
import threading
import time
import sys
import urllib.request
from dotenv import load_dotenv

load_dotenv()

os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
# Contexto ampliado para Ollama — evita saturación en conversaciones largas
os.environ.setdefault("OLLAMA_NUM_CTX", "8192")

try:
    from crewai.events.listeners.tracing.utils import set_suppress_tracing_messages
    set_suppress_tracing_messages(True)
except ImportError:
    pass

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='agent_errors.log',
    filemode='a'
)

# Singletons — instanciados una sola vez, no en cada llamada
_search_tool = DuckDuckGoSearchRun()
_python_repl = PythonREPLTool()

# ==========================================
# HERRAMIENTAS
# ==========================================

@tool("Buscador_Internet")
def herramienta_busqueda(consulta: str) -> str:
    """Útil para buscar información en internet. Pasa la consulta como texto."""
    return _search_tool.run(consulta)

@tool("Ejecutor_Python")
def herramienta_python(codigo: str) -> str:
    """Útil para ejecutar código Python y verificar si funciona. Devuelve la salida de consola."""
    return _python_repl.run(codigo)

@tool("escritor_archivos")
def herramienta_escribir_archivo(ruta_archivo: str, contenido: str) -> str:
    """
    Útil para crear un archivo nuevo o sobrescribir uno existente con código generado.
    Pasa la ruta del archivo (ej. 'src/main.py') y el contenido completo en texto plano.
    """
    try:
        directorio = os.path.dirname(ruta_archivo)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
            archivo.write(contenido)
        return f"Éxito: Archivo guardado en: {os.path.abspath(ruta_archivo)}"
    except Exception as e:
        return f"Error al guardar el archivo: {e}"

@tool("lector_archivos")
def herramienta_leer_archivo(ruta_archivo: str) -> str:
    """Útil para leer el contenido de un archivo existente. Debes pasar la ruta del archivo."""
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return archivo.read()
    except Exception as e:
        return f"Error al leer el archivo: {e}"

@tool("ejecutor_terminal")
def herramienta_terminal(comando: str) -> str:
    """Útil para ejecutar comandos en la terminal (ej. pip install, git, ls, python script.py). Devuelve la salida."""
    try:
        resultado = subprocess.run(
            comando, shell=True, capture_output=True, text=True, timeout=120
        )
        salida = resultado.stdout or ""
        error = resultado.stderr or ""
        if resultado.returncode == 0:
            return f"Éxito:\n{salida}"
        else:
            return f"Error (código {resultado.returncode}):\n{error}\n{salida}"
    except subprocess.TimeoutExpired:
        return "Error: el comando superó el tiempo límite de 120 segundos."
    except Exception as e:
        return f"Excepción al ejecutar: {e}"

@tool("Listador_Carpetas")
def herramienta_listar(ruta_directorio: str) -> str:
    """Útil para ver qué archivos y carpetas existen en un directorio, con tipo y tamaño."""
    try:
        entries = []
        with os.scandir(ruta_directorio) as it:
            for entry in sorted(it, key=lambda e: (not e.is_dir(), e.name)):
                if entry.is_dir():
                    entries.append(f"📁 {entry.name}/")
                else:
                    size = entry.stat().st_size
                    size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"
                    entries.append(f"📄 {entry.name}  ({size_str})")
        return f"Contenido de '{ruta_directorio}':\n" + "\n".join(entries)
    except Exception as e:
        return f"Error al leer la carpeta: {e}"

@tool("Reemplazar_En_Archivo")
def herramienta_reemplazar(ruta_archivo: str, texto_antiguo: str, texto_nuevo: str) -> str:
    """Útil para cambiar un bloque específico de código sin reescribir todo el archivo."""
    try:
        if not os.path.exists(ruta_archivo):
            return f"El archivo '{ruta_archivo}' no existe."
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        if texto_antiguo not in contenido:
            return "No se encontró 'texto_antiguo'. Asegúrate de que coincida exactamente."
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido.replace(texto_antiguo, texto_nuevo, 1))
        return f"Archivo '{ruta_archivo}' modificado correctamente."
    except Exception as e:
        return f"Error al reemplazar texto: {e}"

@tool("Lector_Paginas_Web")
def herramienta_web(url: str) -> str:
    """Útil para leer el contenido de texto de una página web o documentación online."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
        texto = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        texto = re.sub(r'<script.*?</script>', '', texto, flags=re.DOTALL | re.IGNORECASE)
        texto = re.sub(r'<[^>]+>', ' ', texto)
        return re.sub(r'\s+', ' ', texto).strip()[:15000]
    except Exception as e:
        return f"Error al leer la web: {e}"

@tool("Preguntar_Usuario")
def herramienta_preguntar(pregunta: str) -> str:
    """Útil cuando tienes una duda importante o necesitas aclaración antes de continuar. Pregunta al usuario."""
    print(f"\n🙋 [El agente necesita aclaración]: {pregunta}")
    sys.stdout.flush()
    respuesta = input("Tú (respuesta): ")
    print("🤖 Retomando ejecución...")
    return respuesta

# Herramientas activas — preguntar_usuario evita alucinaciones en tareas ambiguas
mis_herramientas = [
    herramienta_escribir_archivo,
    herramienta_leer_archivo,
    herramienta_terminal,
    herramienta_preguntar,
]

# ==========================================
# CONFIGURACIÓN LLM
# ==========================================

OLLAMA_BASE_URL = os.getenv('OLLAMA_API_BASE', 'http://localhost:11434')

# Backstory compartido — mantenido en una sola variable para no duplicar
BACKSTORY = (
    "Eres un Ingeniero de Software Senior meticuloso. Tu proceso:\n"
    "1. Analiza la petición antes de escribir código.\n"
    "2. Usa `ejecutor_terminal` para crear proyectos (django-admin startproject, npm init, etc.).\n"
    "3. Usa `escritor_archivos` para crear o modificar código.\n"
    "4. Si la petición es ambigua, usa `Preguntar_Usuario` antes de continuar.\n"
    "5. SIEMPRE usa este formato exacto al llamar herramientas (sin espacios al inicio):\n"
    "Thought: [tu razonamiento]\n"
    "Action: [nombre_exacto_de_la_herramienta]\n"
    "Action Input: {\"parametro\": \"valor\"}\n"
    "¡PARA inmediatamente tras Action Input! No añadas ningún texto después."
)

# Intentar usar la clase LLM de crewai (versiones recientes) para pasar num_ctx
try:
    from crewai import LLM
    llm_ollama = LLM(
        model='ollama/llama3.1:8b',
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        num_ctx=8192,
    )
    _llm_ollama_str = None
except (ImportError, Exception):
    # Fallback: string + env var OLLAMA_NUM_CTX ya establecida arriba
    llm_ollama = 'ollama/llama3.1:8b'
    _llm_ollama_str = llm_ollama

# ==========================================
# AGENTES
# ==========================================

programador = Agent(
    role='Ingeniero de Software Senior',
    goal='Crear código correcto, guardarlo en archivos y ejecutar comandos para validarlo.',
    backstory=BACKSTORY,
    tools=mis_herramientas,
    verbose=False,
    llm=llm_ollama,
    allow_delegation=False,
    cache=True,
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
programador_gemini = None
if GEMINI_API_KEY:
    try:
        from crewai import LLM as _LLM
        llm_gemini = _LLM(model='gemini/gemini-2.0-flash', temperature=0.1)
    except (ImportError, Exception):
        llm_gemini = 'gemini/gemini-2.0-flash'
    programador_gemini = Agent(
        role='Ingeniero de Software Senior',
        goal='Crear código correcto, guardarlo en archivos y ejecutar comandos para validarlo.',
        backstory=BACKSTORY,
        tools=mis_herramientas,
        verbose=False,
        llm=llm_gemini,
        allow_delegation=False,
        cache=True,
    )

# ==========================================
# SPINNER
# ==========================================

def spinner(stop_event, start_time, label="Programador"):
    chars = ['-', '\\', '|', '/']
    while not stop_event.is_set():
        elapsed = time.strftime('%M:%S', time.gmtime(time.time() - start_time))
        for c in chars:
            if stop_event.is_set():
                break
            sys.stdout.write(f'\r   [2/3] 👩‍💻  {label} trabajando... [{elapsed}] {c}')
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * 70 + '\r')
    sys.stdout.flush()

# ==========================================
# ARRANQUE
# ==========================================

print("==================================================")
print("📥 Comprobando modelo en Ollama...")
print("   (Si Ollama corre en Podman, el modelo se gestiona desde el contenedor)")
_ollama_cli = shutil.which("ollama")
if _ollama_cli:
    os.system(f"{_ollama_cli} pull llama3.1:8b")

_gemini_status = (
    "✅ Gemini 2.0 Flash configurado como respaldo"
    if GEMINI_API_KEY else
    "⚠️  Sin Gemini (añade GEMINI_API_KEY en .env para activarlo)"
)
print("==================================================")
print("🤖 AGENTE INICIADO")
print(f"   🦙 Principal : llama3.1:8b  |  ctx: 8192 tokens  |  temp: 0.1")
print(f"   {_gemini_status}")
print("Escribe 'salir' para terminar el chat.")
print("==================================================\n")

# ==========================================
# BUCLE PRINCIPAL
# ==========================================

# Regex de extensiones de fichero soportadas por el Safety Patch
_EXT_RE = r'([\w/.-]+\.(?:py|js|ts|jsx|tsx|html|css|json|yaml|yml|sh|md|txt|env|sql|java|go|rs|cpp|c|h|vue|svelte|rb|php))'

# Historial como lista para poder truncarlo fácilmente
_MAX_TURNOS = 6          # pares usuario/agente a conservar en contexto
historial_lista: list[str] = []

DIRECTORIO_TRABAJO = os.getcwd()

while True:
    orden_usuario = input("\n👤 Tú: ")

    if orden_usuario.lower() in ['salir', 'exit', 'quit']:
        print("Apagando agente... ¡Hasta luego!")
        break

    if not orden_usuario.strip():
        continue

    print("\n🤖 Procesando tu petición...")
    print("   [1/3] 📋  Preparando tarea...")

    historial_lista.append(f"- Usuario: {orden_usuario}")
    # Solo los últimos N*2 elementos (cada turno = 1 usuario + 1 agente)
    historial_texto = "\n".join(historial_lista[-_MAX_TURNOS * 2:])

    tarea_principal = Task(
        description=(
            f"Directorio de trabajo actual: {DIRECTORIO_TRABAJO}\n\n"
            f"HISTORIAL (últimas {_MAX_TURNOS} interacciones):\n{historial_texto}\n\n"
            f"PETICIÓN ACTUAL: '{orden_usuario}'\n\n"
            "RECUERDA el formato obligatorio para herramientas:\n"
            "Thought: [razonamiento]\n"
            "Action: [nombre_herramienta]\n"
            "Action Input: {\"param\": \"valor\"}\n\n"
            "Usa escritor_archivos para guardar cada fichero. Si son varios, úsalo varias veces."
        ),
        expected_output="Ruta absoluta de los archivos guardados, o resultado del comando ejecutado.",
        agent=programador
    )

    equipo = Crew(
        agents=[programador],
        tasks=[tarea_principal],
        process=Process.sequential,
        verbose=False,
        max_iter=10,
    )

    try:
        resultado = None
        _usando_gemini = False

        # Intento 1: Ollama local
        stop_ev = threading.Event()
        hilo = threading.Thread(target=spinner, args=(stop_ev, time.time(), "Ollama"))
        try:
            hilo.start()
            resultado = equipo.kickoff()
        except Exception as _e_ollama:
            if not programador_gemini:
                raise
            print(f"\n⚠️ Ollama falló ({type(_e_ollama).__name__}). Escalando a Gemini...")
        finally:
            stop_ev.set()
            hilo.join()

        # Intento 2: Gemini fallback
        if resultado is None and programador_gemini:
            tarea_gemini = Task(
                description=tarea_principal.description,
                expected_output=tarea_principal.expected_output,
                agent=programador_gemini
            )
            equipo_gemini = Crew(
                agents=[programador_gemini],
                tasks=[tarea_gemini],
                process=Process.sequential,
                verbose=False,
                max_iter=10,
            )
            stop_ev2 = threading.Event()
            hilo2 = threading.Thread(target=spinner, args=(stop_ev2, time.time(), "Gemini"))
            try:
                hilo2.start()
                resultado = equipo_gemini.kickoff()
                _usando_gemini = True
            finally:
                stop_ev2.set()
                hilo2.join()

        print("\n   [3/3] ✅ ¡Proceso completado!")

        # ==========================================
        # SISTEMA DE SEGURIDAD (SAFETY PATCH)
        # ==========================================
        resultado_texto = str(resultado)
        try:
            code_match = re.search(r'```(?:\w+)?\s*([\s\S]*?)```', resultado_texto)

            # Parche emergencia terminal — subprocess con captura de salida
            for cmd in re.findall(r'"comando"\s*:\s*"([^"]+)"', resultado_texto):
                print(f"\n   [!] Parche terminal: ejecutando → {cmd}")
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                out = r.stdout or r.stderr
                print(f"   [!] {'OK' if r.returncode == 0 else 'ERROR'}: {out[:200]}")

            json_args = {}
            # Busca el primer JSON completo (no codicioso en llaves anidadas)
            json_match = re.search(r'(\{[^{}]*\})', resultado_texto, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    json_args = data.get("arguments", data)
                    if isinstance(json_args, str):
                        json_args = json.loads(json_args)
                except Exception:
                    pass

            contenido_final = ruta_final = None

            if code_match:
                contenido_final = code_match.group(1).strip()
                if isinstance(json_args, dict) and "ruta_archivo" in json_args:
                    ruta_final = json_args["ruta_archivo"]
                else:
                    m = re.search(_EXT_RE, orden_usuario + " " + resultado_texto)
                    ruta_final = m.group(1) if m else "script_generado.py"

            elif isinstance(json_args, dict) and "contenido" in json_args and "ruta_archivo" in json_args:
                contenido_final = json_args["contenido"]
                ruta_final = json_args["ruta_archivo"]

            else:
                for key in ('"contenido"', '"codigo"'):
                    idx = resultado_texto.find(key)
                    if idx == -1:
                        continue
                    bloque = resultado_texto[idx:].split(':', 1)[1].strip()
                    for q in ('"""', "'''", '"'):
                        if bloque.startswith(q):
                            end = bloque.find(q, len(q))
                            bloque = bloque[len(q):end] if end != -1 else bloque[len(q):]
                            bloque = bloque.replace('\\n', '\n').replace('\\"', '"')
                            break
                    else:
                        end = bloque.rfind('}')
                        if end != -1:
                            bloque = bloque[:end]
                    contenido_final = bloque.strip()
                    m = re.search(r'"ruta_archivo"\s*:\s*["\']([^"\']+)["\']', resultado_texto)
                    ruta_final = m.group(1) if m else (
                        re.search(_EXT_RE, orden_usuario + " " + resultado_texto) or [None, "script_generado.py"]
                    )[1]
                    break

            if contenido_final and ruta_final:
                directorio = os.path.dirname(ruta_final)
                if directorio:
                    os.makedirs(directorio, exist_ok=True)
                for tag in ("```python", "```"):
                    if contenido_final.startswith(tag):
                        contenido_final = contenido_final[len(tag):].strip()
                if contenido_final.endswith("```"):
                    contenido_final = contenido_final[:-3].strip()
                with open(ruta_final, 'w', encoding='utf-8') as f:
                    f.write(contenido_final)
                resultado_texto = f"✅ Archivo guardado en: {ruta_final}"

        except Exception as parse_error:
            logging.error(f"Safety Patch error: {parse_error}")

        modelo_usado = "GEMINI ✨" if _usando_gemini else "OLLAMA 🦙"
        print(f"\n--- RESPUESTA [{modelo_usado}] ---")
        print(resultado_texto)

        # Guardar resumen en historial — nunca el código completo
        resumen = resultado_texto if len(resultado_texto) <= 300 else resultado_texto[:297] + "..."
        historial_lista.append(f"- Agente: {resumen}")

    except Exception as e:
        print(f"\n⚠️ El agente falló. Error: {e}")
        print("💡 Intenta ser más específico o divide la tarea en pasos.")

    print("------------------------------------------------------------------\n")
