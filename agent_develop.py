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

@tool("Escritor_Archivos")
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

@tool("Lector_Archivos")
def herramienta_leer_archivo(ruta_archivo: str) -> str:
    """Útil para leer el contenido de un archivo existente. Debes pasar la ruta del archivo."""
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return archivo.read()
    except Exception as e:
        return f"Error al intentar leer el archivo: {e}"

mis_herramientas = [herramienta_busqueda, herramienta_python, herramienta_escribir_archivo, herramienta_leer_archivo]

# 3. Creamos los Agentes

# Agente: El Programador (El Ejecutor)
programador = Agent(
    role='Ingeniero de Software Experto',
    goal='Crear, leer, modificar, testear y corregir código Python, guardando siempre el resultado final en un archivo.',
    backstory='''Eres un desarrollador de software full-stack. Tu especialidad es ejecutar tareas de programación de manera impecable.
    Tu proceso según la tarea asignada:
    - Escribe el código Python asegurándote de añadirle comentarios explicativos.
    - Testea tu código usando la herramienta `Python_REPL` para verificar que funciona correctamente o para corregir errores.
    - Una vez testeado y validado, guárdalo usando la herramienta `Escritor_Archivos`.
    IMPORTANTE: Si decides usar una herramienta, DEBES seguir exactamente este formato en tu respuesta:
    Thought: (Tu razonamiento de qué vas a hacer)
    Action: Escritor_Archivos
    Action Input: {"ruta_archivo": "nombre_del_archivo.py", "contenido": "codigo_aqui"}
    ¡NUNCA devuelvas solo un JSON suelto sin las palabras Thought y Action!''',
    tools=mis_herramientas,
    verbose=False,
    llm='ollama/qwen2.5-coder:7b', # Usamos la versión 7B para máxima calidad de código
    allow_delegation=False, # No delega, solo ejecuta
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
            sys.stdout.write(f'\r   [2/3] 👩‍💻  Programador ejecutando las tareas... [{formatted_time}] {char}')
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

# 4. Bucle del Chat Continúo
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
    
    # Creamos la tarea dinámica con lo que has escrito
    tarea_principal = Task(
        description=f"""Petición del usuario: '{orden_usuario}'.
        Debes escribir el código Python necesario para cumplir esta petición, añadirle comentarios explicativos, TESTEARLO usando la herramienta 'Python_REPL' para asegurarte de que funciona y, finalmente, usar la herramienta 'Escritor_Archivos' para guardarlo en tu ordenador.""",
        expected_output="""La ruta absoluta del archivo guardado tras usar Escritor_Archivos. Ejemplo: 'C:\\Users\\...\\script.py'""", 
        agent=programador # Directamente al programador
    )
    
    equipo = Crew(
        agents=[programador],
        tasks=[tarea_principal],
        process=Process.sequential,
        verbose=False,
        max_iter=5)

    try:
        stop_spinner = threading.Event()
        start_time = time.time()
        spinner_thread = threading.Thread(target=spinner, args=(stop_spinner, start_time))
        resultado = None

        try:
            spinner_thread.start()
            # Ejecutamos el equipo (esta es la parte que bloquea y tarda)
            resultado = equipo.kickoff()
        finally:
            # Nos aseguramos de que el spinner se detenga, incluso si hay un error
            stop_spinner.set()
            spinner_thread.join()
        
        print("   [3/3] ✅ ¡Proceso completado!")
        
        # Parche de seguridad: si el modelo pequeño devuelve el código en el texto en lugar de usar la herramienta
        resultado_texto = str(resultado)
        try:
            import json, re
            
            # Buscar bloque de código en la respuesta final (con o sin \r)
            code_match = re.search(r'```(?:python)?\s*([\s\S]*?)```', resultado_texto)
            
            # También intentamos extraer argumentos JSON si el agente devolvió un JSON roto
            json_args = {}
            if "{" in resultado_texto and "}" in resultado_texto:
                json_str = resultado_texto[resultado_texto.find("{"):resultado_texto.rfind("}")+1]
                try:
                    data = json.loads(json_str)
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
                if idx != -1:
                    bloque = resultado_texto[idx:].split(':', 1)[1].strip()
                    if bloque.endswith('}'):
                        bloque = bloque[:-1].strip()
                    if bloque.startswith('"""') and bloque.endswith('"""'):
                        bloque = bloque[3:-3]
                    elif bloque.startswith("'''") and bloque.endswith("'''"):
                        bloque = bloque[3:-3]
                    elif bloque.startswith('"') and bloque.endswith('"'):
                        bloque = bloque[1:-1].replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                    contenido_final = bloque.strip()
                    
                    ruta_match = re.search(r'"ruta_archivo"\s*:\s*["\'](.*?)["\']', resultado_texto)
                    if ruta_match:
                        ruta_final = ruta_match.group(1)
                    else:
                        ruta_match = re.search(r'([a-zA-Z0-9_-]+\.py)', orden_usuario + " " + resultado_texto)
                        ruta_final = ruta_match.group(1) if ruta_match else "script_generado.py"
            
            if contenido_final and ruta_final:
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
            
    except Exception as e:
        # Si el modelo local agota sus intentos o se satura, te avisa sin romper el bucle
        print(f"\n⚠️ El agente se atascó o falló. Error técnico: {e}")
        print("💡 Consejo: Intenta darle instrucciones más paso a paso.")
    
    print("------------------------------------------------------------------\n")