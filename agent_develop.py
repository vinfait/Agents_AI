from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.tools import PythonREPLTool
import os
from dotenv import load_dotenv
import threading
import time
import sys
import logging

# Carga las variables de entorno desde un archivo .env al iniciar el script.
load_dotenv()

# Desactivar telemetría y mensajes de tracing de CrewAI
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
try:
    from crewai.events.listeners.tracing.utils import set_suppress_tracing_messages
    set_suppress_tracing_messages(True)
except ImportError:
    pass

# Configura el logging para que los errores y advertencias se guarden en un archivo
# en lugar de mostrarse en la consola.
logging.basicConfig(
    level=logging.WARNING,  # Captura desde advertencias (WARNING) hacia arriba (ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='agent_errors.log', # Nombre del archivo de log
    filemode='a'  # 'a' para añadir logs en cada ejecución, 'w' para sobrescribir
)

# 1. Configuramos las herramientas con el formato nativo de CrewAI
@tool("Buscador_Internet")
def herramienta_busqueda(consulta: str) -> str:
    """Útil para buscar información en internet. Pasa la consulta como texto."""
    return DuckDuckGoSearchRun().run(consulta)

@tool("Ejecutor_Python")
def herramienta_python(codigo: str) -> str:
    """Útil para ejecutar código Python y verificar si funciona. Devuelve la salida de consola."""
    return PythonREPLTool().run(codigo)

@tool("escritor_archivos")
def herramienta_escribir_archivo(ruta_archivo: str, contenido: str) -> str:
    """
    Útil para crear un archivo nuevo o sobrescribir uno existente con código generado.
    Debes pasar la ruta del archivo (ej. 'mi_script.py') y el contenido en texto plano.
    """
    try:
        # Aseguramos que la carpeta exista antes de guardar
        directorio = os.path.dirname(ruta_archivo)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
            
        # Abrimos el archivo en modo escritura ('w' sobrescribe, 'a' añade al final)
        with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
            archivo.write(contenido)
            
        ruta_absoluta = os.path.abspath(ruta_archivo)
        return f"Éxito: El código se ha guardado correctamente en la ruta absoluta: {ruta_absoluta}"
    except Exception as e:
        return f"Error al intentar guardar el archivo: {e}"

@tool("lector_archivos")
def herramienta_leer_archivo(ruta_archivo: str) -> str:
    """Útil para leer el contenido de un archivo existente. Debes pasar la ruta del archivo."""
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return archivo.read()
    except Exception as e:
        return f"Error al intentar leer el archivo: {e}"

@tool("ejecutor_terminal")
def herramienta_terminal(comando: str) -> str:
    """Útil para ejecutar comandos en la terminal (ej. pip install, git, docker, ls). Devuelve la salida del comando."""
    try:
        import subprocess
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=120)
        salida = resultado.stdout if resultado.stdout else ""
        error = resultado.stderr if resultado.stderr else ""
        if resultado.returncode == 0:
            return f"Comando ejecutado con éxito:\n{salida}"
        else:
            return f"Error al ejecutar el comando (Código {resultado.returncode}):\n{error}\n{salida}"
    except Exception as e:
        return f"Excepción al intentar ejecutar: {e}"

@tool("Listador_Carpetas")
def herramienta_listar(ruta_directorio: str) -> str:
    """Útil para ver qué archivos y carpetas existen en un directorio. Pasa la ruta (ej. '.' para la actual)."""
    try:
        import os
        archivos = os.listdir(ruta_directorio)
        return f"Contenido de '{ruta_directorio}':\n" + "\n".join(archivos)
    except Exception as e:
        return f"Error al leer la carpeta: {e}"

@tool("Reemplazar_En_Archivo")
def herramienta_reemplazar(ruta_archivo: str, texto_antiguo: str, texto_nuevo: str) -> str:
    """Útil para cambiar un bloque específico de código sin reescribir todo el archivo. Pasa la ruta, el texto a buscar y el nuevo texto."""
    try:
        import os
        if not os.path.exists(ruta_archivo):
            return f"El archivo {ruta_archivo} no existe."
            
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
            
        if texto_antiguo not in contenido:
            return "No se encontró el 'texto_antiguo' en el archivo. Asegúrate de que coincida exactamente (¡cuidado con espacios y saltos de línea!)."
            
        nuevo_contenido = contenido.replace(texto_antiguo, texto_nuevo, 1) # Reemplaza la primera ocurrencia
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(nuevo_contenido)
            
        return f"Archivo {ruta_archivo} modificado correctamente."
    except Exception as e:
        return f"Error al reemplazar texto: {e}"

@tool("Lector_Paginas_Web")
def herramienta_web(url: str) -> str:
    """Útil para leer el contenido de texto de una página web o documentación online."""
    try:
        import urllib.request
        import re
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            # Extraer texto básico sin etiquetas HTML
            texto = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            texto = re.sub(r'<script.*?</script>', '', texto, flags=re.DOTALL | re.IGNORECASE)
            texto = re.sub(r'<[^>]+>', ' ', texto)
            texto = re.sub(r'\s+', ' ', texto).strip()
            return texto[:15000] # Limitar tamaño para no saturar memoria
    except Exception as e:
        return f"Error al leer la web: {e}"

@tool("Preguntar_Usuario")
def herramienta_preguntar(pregunta: str) -> str:
    """Útil para preguntarle al usuario humano cuando tienes una duda importante, necesitas permisos o no sabes cómo continuar."""
    print(f"\n🙋‍♂️ [Pregunta del Agente]: {pregunta}")
    # Limpiamos los saltos de línea del print para que el usuario responda abajo
    sys.stdout.flush()
    respuesta = input("Tú (Respuesta al Agente): ")
    print("🤖 Retomando ejecución...")
    return respuesta

mis_herramientas = [
    herramienta_escribir_archivo, 
    herramienta_leer_archivo,
    herramienta_terminal
]

# ==========================================
# 3. CREACIÓN DEL AGENTE CENTRAL
# ==========================================
# Aquí definimos la "personalidad" y el rol de nuestro asistente.
# Al usar un modelo local de 7B, un solo agente "Todoterreno" 
# es más estable que un sistema de 3 agentes debatiendo.
llm_model = 'ollama/qwen2.5-coder:7b'

# Agente: El Programador (El Todoterreno)
programador = Agent(
    role='Ingeniero de Software Senior',
    goal='Crear código, guardarlo en archivos y ejecutar comandos en la terminal para testear.',
    backstory='''Eres un desarrollador meticuloso. Tu proceso es sencillo y estricto:
    1. Si necesitas crear un proyecto (ej. Django, Node), usa `ejecutor_terminal` para lanzar comandos como `django-admin startproject` o `npm init`.
    2. Usa `escritor_archivos` para crear archivos de código nuevos.
    3. Si usas una herramienta, DEBES SIEMPRE respetar este formato exacto SIN ESPACIOS AL INICIO DE LA LÍNEA:
Thought: [tu pensamiento]
Action: [nombre de la herramienta]
Action Input: {"parametro": "valor"}
    ¡NO ESCRIBAS NINGÚN TEXTO DESPUÉS DE 'Action Input:'! ¡Para de escribir inmediatamente!
    ¡NUNCA DEVUELVAS UN ARRAY JSON NI UNA LISTA DE FUNCIONES! ¡USA SIEMPRE EL FORMATO THOUGHT/ACTION!''',
    tools=mis_herramientas,
    verbose=False,
    llm=llm_model,
    allow_delegation=False,
    cache=True
)

def spinner(stop_event, start_time):
    """Muestra una animación de cursor giratorio con un cronómetro en tiempo real."""
    spinner_chars = ['-', '\\', '|', '/']
    while not stop_event.is_set():
        elapsed_time = time.time() - start_time
        # Formateamos el tiempo transcurrido en formato MM:SS
        formatted_time = time.strftime('%M:%S', time.gmtime(elapsed_time))

        for char in spinner_chars:
            if stop_event.is_set():
                break
            # Escribe el mensaje y el spinner, \r vuelve al inicio de la línea
            sys.stdout.write(f'\r   [2/3] 👩‍💻  Programador trabajando... [{formatted_time}] {char}')
            sys.stdout.flush()
            time.sleep(0.1)
    # Limpia la línea del spinner antes de que se imprima el resultado final
    sys.stdout.write('\r' + ' ' * 70 + '\r')
    sys.stdout.flush()

print("==================================================")
print("📥 Comprobando/descargando el modelo Qwen2.5-Coder:7B...")
print("   (Esto puede tardar unos minutos la primera vez)")
os.system("ollama pull qwen2.5-coder:7b")

print("==================================================")
print("🤖 EQUIPO DE AGENTES INICIADO (Manager y Programador)")
print("Escribe 'salir' para terminar el chat.")
print("==================================================\n")

# ==========================================
# 4. BUCLE PRINCIPAL DEL CHAT
# ==========================================
# Este bucle mantiene el programa vivo, esperando órdenes del usuario,
# procesándolas y guardando la conversación en la "memoria".
historial_conversacion = ""

while True:
    orden_usuario = input("\n👤 Tú: ")
    
    # Salir del programa
    if orden_usuario.lower() in ['salir', 'exit', 'quit']:
        print("Apagando agente... ¡Hasta luego!")
        break
        
    # Ignorar inputs vacíos
    if not orden_usuario.strip():
        continue

    print("\n🤖 Procesando tu petición...")
    print("   [1/3] 🕵️‍♂️  Manager analizando y creando el plan...")
    # El equipo ahora trabaja en segundo plano. El cursor parpadeará mientras procesan.
    
    historial_conversacion += f"\n- Usuario: {orden_usuario}"
    
    # Creamos la tarea dinámica con lo que has escrito
    tarea_principal = Task(
        description=f"""HISTORIAL DE CONTEXTO (Lo que hemos hablado hasta ahora):
        {historial_conversacion}

        PETICIÓN ACTUAL DEL USUARIO: '{orden_usuario}'.
        Debes usar todas tus herramientas para cumplir la petición: explora, escribe, testea y finalmente usa 'Escritor_Archivos' para guardarlo.
        Si son múltiples archivos, usa la herramienta múltiples veces.""",
        expected_output="""La ruta absoluta de los archivos guardados o modificados tras usar Escritor_Archivos.""", 
        agent=programador
    )
    
    equipo = Crew(
        agents=[programador],
        tasks=[tarea_principal],
        process=Process.sequential,
        verbose=False,
        max_iter=25)

    try:
        stop_spinner = threading.Event()
        start_time = time.time()
        spinner_thread = threading.Thread(target=spinner, args=(stop_spinner, start_time))
        resultado = None

        try:
            spinner_thread.start()
            resultado = equipo.kickoff()
        finally:
            stop_spinner.set()
            spinner_thread.join()
            
        print("\n   [3/3] ✅ ¡Proceso completado!")
        
        # ==========================================
        # 5. SISTEMA DE SEGURIDAD (FALLBACKS)
        # ==========================================
        # Si el modelo LLM se equivoca y devuelve el código como texto plano
        # en lugar de usar la herramienta Escritor_Archivos correctamente, 
        # este bloque atrapa el código y crea el archivo manualmente.
        resultado_texto = str(resultado)
        try:
            import json, re
            
            # Intento 1: Buscar si el agente escupió un bloque de markdown ```python ... ```
            code_match = re.search(r'```(?:python)?\s*([\s\S]*?)```', resultado_texto)
            
            # ¡PARCHE DE EMERGENCIA PARA LA TERMINAL!
            # Extraemos cualquier comando que haya intentado usar con regex para evitar errores de parseo JSON
            comandos_hallados = re.findall(r'"comando"\s*:\s*"([^"]+)"', resultado_texto)
            for cmd in comandos_hallados:
                print(f"\n   [!] Parche de Emergencia Activado: Ejecutando comando -> {cmd}")
                import os
                os.system(cmd)
                print("   [!] Comando ejecutado con éxito por el sistema de seguridad.")
                
            # Intentamos extraer ruta_archivo y contenido de la misma forma robusta
            json_args = {}
            if "{" in resultado_texto and "}" in resultado_texto:
                # Buscamos el primer bloque JSON no-codicioso para evitar que se trague varios JSONs juntos
                json_match = re.search(r'(\{.*?\})', resultado_texto, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        json_args = data.get("arguments", data)
                        if isinstance(json_args, str):
                            json_args = json.loads(json_args)
                    except:
                        pass
            
            contenido_final = None
            ruta_final = None
            
            if code_match:
                # Si escupió el código en markdown, lo priorizamos porque suele ser el código completo
                contenido_final = code_match.group(1).strip()
                # Buscamos el nombre del archivo en el JSON, en la respuesta, o en la orden del usuario
                if isinstance(json_args, dict) and "ruta_archivo" in json_args:
                    ruta_final = json_args["ruta_archivo"]
                else:
                    ruta_match = re.search(r'([a-zA-Z0-9_-]+\.py)', orden_usuario + " " + resultado_texto)
                    ruta_final = ruta_match.group(1) if ruta_match else "script_generado.py"
                    
            elif isinstance(json_args, dict) and "contenido" in json_args and "ruta_archivo" in json_args:
                # Si no hay bloque markdown, pero logramos parsear el JSON
                contenido_final = json_args["contenido"]
                ruta_final = json_args["ruta_archivo"]
            else:
                # Fallback final: cortar strings manualmente
                idx = resultado_texto.find('"contenido"')
                if idx == -1:
                    idx = resultado_texto.find('"codigo"')
                    
                if idx != -1:
                    bloque = resultado_texto[idx:].split(':', 1)[1].strip()
                    
                    # Intentar extraer solo lo que hay dentro de comillas triples
                    if bloque.startswith('"""'):
                        end_idx = bloque.find('"""', 3)
                        if end_idx != -1:
                            bloque = bloque[3:end_idx]
                        else:
                            bloque = bloque[3:] # Si se olvidó cerrarlo, cogemos el resto
                    elif bloque.startswith("'''"):
                        end_idx = bloque.find("'''", 3)
                        if end_idx != -1:
                            bloque = bloque[3:end_idx]
                        else:
                            bloque = bloque[3:]
                    elif bloque.startswith('"'):
                        end_idx = bloque.find('"', 1)
                        if end_idx != -1:
                            bloque = bloque[1:end_idx].replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                        else:
                            bloque = bloque[1:].replace('\\n', '\n')
                    else:
                        # Si no empieza por comillas, cortamos en la llave de cierre si la hay
                        end_idx = bloque.rfind('}')
                        if end_idx != -1:
                            bloque = bloque[:end_idx].strip()
                            
                    contenido_final = bloque.strip()
                    
                    ruta_match = re.search(r'"ruta_archivo"\s*:\s*["\'](.*?)["\']', resultado_texto)
                    if ruta_match:
                        ruta_final = ruta_match.group(1)
                    else:
                        ruta_match = re.search(r'([a-zA-Z0-9_-]+\.py)', orden_usuario + " " + resultado_texto)
                        ruta_final = ruta_match.group(1) if ruta_match else "script_generado.py"
            
            if contenido_final and ruta_final:
                # Crear la carpeta si no existe
                import os
                directorio = os.path.dirname(ruta_final)
                if directorio:
                    os.makedirs(directorio, exist_ok=True)
                    
                # Limpiar etiquetas residuales si existen
                if contenido_final.startswith("```python"):
                    contenido_final = contenido_final[9:].strip()
                if contenido_final.startswith("```"):
                    contenido_final = contenido_final[3:].strip()
                if contenido_final.endswith("```"):
                    contenido_final = contenido_final[:-3].strip()
                    
                with open(ruta_final, 'w', encoding='utf-8') as f:
                    f.write(contenido_final)
                
                resultado_texto = f"✅ El agente escribió y testeó el código correctamente. Archivo guardado en: {ruta_final}"
                
        except Exception as parse_error:
            # En caso de error en el parche, registramos en el log
            import logging
            logging.error(f"Error en parche de seguridad: {parse_error}")
            
        print("\n--- RESPUESTA DEL EQUIPO ---")
        print(resultado_texto)
        
        # Guardamos la respuesta del agente en el historial para que lo recuerde la próxima vez
        historial_conversacion += f"\n- Agente: {resultado_texto}"
            
    except Exception as e:
        # Si el modelo local agota sus intentos o se satura, te avisa sin romper el bucle
        print(f"\n⚠️ El agente se atascó o falló. Error técnico: {e}")
        print("💡 Consejo: Intenta darle instrucciones más paso a paso.")
    
    print("------------------------------------------------------------------\n")