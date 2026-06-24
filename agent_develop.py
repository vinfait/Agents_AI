from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool
from langchain_google_community import GoogleSearchRun
from langchain_experimental.tools import PythonREPLTool
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde un archivo .env al iniciar el script.
load_dotenv()

# 1. Configuramos las herramientas con el formato nativo de CrewAI
# Para usar la búsqueda de Google, necesitas configurar dos variables de entorno:
# 1. GOOGLE_API_KEY: Tu clave de API de Google Cloud.
# 2. GOOGLE_CSE_ID: El ID de tu motor de búsqueda programable.
# Visita https://developers.google.com/custom-search/v1/overview para más detalles.
@tool("Buscador_Internet")
def herramienta_busqueda(consulta: str) -> str:
    """Útil para buscar información en internet. Pasa la consulta como texto."""
    return GoogleSearchRun().run(consulta)

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
            
        return f"Éxito: El código se ha guardado correctamente en {ruta_archivo}"
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

# 2. Configuramos el motor local (Ollama)
# Asegúrate de tener Ollama corriendo en tu máquina con el modelo descargado
llm_ollama = LLM(
    model="ollama/qwen2:7b-instruct",
    base_url="http://localhost:11434"
)

# 3. Creamos el Agente Local
programador = Agent(
    role='Ingeniero de Software Experto',
    goal='Crear, leer, modificar, testear y corregir código Python, guardando siempre el resultado final en un archivo.',
    backstory='''Eres un desarrollador de software full-stack. Tu especialidad es gestionar el ciclo de vida completo del código.
    Tu proceso varía según la tarea:
    - Para **CREAR** un script: Escribe el código, pruébalo con `Ejecutor_Python` y guárdalo con `Escritor_Archivos`.
    - Para **MODIFICAR** o **CORREGIR** un script: DEBES usar `Lector_Archivos` para leer el contenido del archivo primero. Luego, modifica el código en tu pensamiento, pruébalo con `Ejecutor_Python` y, si funciona, sobrescribe el archivo original usando `Escritor_Archivos` con el contenido nuevo y corregido.
    Tu trabajo siempre termina guardando un archivo. Tu respuesta final debe ser la confirmación del archivo guardado.''',
    llm=llm_ollama, 
    tools=mis_herramientas,
    verbose=True,
    max_iter=10,
    allow_delegation=False
)

print("==================================================")
print("🤖 AGENTE INICIADO (100% Local con OLLAMA)")
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

    print("\n🤖 Procesando en local...")
    
    # Creamos la tarea dinámica con lo que has escrito
    tarea = Task(
        description=f"""Analiza la petición del usuario: '{orden_usuario}'.
        Sigue rigurosamente el flujo de trabajo definido en tu 'backstory' (crear o modificar/corregir).
        Si el usuario pide modificar o corregir un archivo, DEBES usar la herramienta `Lector_Archivos` antes de hacer cualquier otra cosa.
        El resultado final siempre debe ser un archivo guardado en disco.""",
        expected_output="La confirmación de que el archivo .py ha sido creado, modificado o corregido y guardado exitosamente.", 
        agent=programador
    )
    
    equipo = Crew(agents=[programador], tasks=[tarea])

    try:
        # Ejecutamos el agente
        resultado = equipo.kickoff()
        print("\n--- RESPUESTA DEL AGENTE ---")
        print(resultado)
    except Exception as e:
        # Si el modelo local agota sus intentos o se satura, te avisa sin romper el bucle
        print(f"\n⚠️ El agente se atascó o falló. Error técnico: {e}")
        print("💡 Consejo: Intenta darle instrucciones más paso a paso.")
    
    print("----------------------------\n")