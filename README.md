# 🤖 Agents AI - Tu Desarrollador Autónomo Local

Bienvenido a **Agents AI**, un script avanzado que transforma tu terminal en un asistente de desarrollo de software autónomo propulsado por IA. Este proyecto utiliza un **Agente "Todoterreno" de nivel Senior** diseñado específicamente para ejecutarse de forma 100% local en ordenadores con memoria RAM limitada (usando modelos de 7B de parámetros como `qwen2.5-coder`), garantizando la máxima estabilidad sin sacrificar potencia.

## ✨ Características Principales

- **Privacidad Total**: Todo se ejecuta en local a través de [Ollama](https://ollama.com/), sin enviar tu código a APIs de terceros.
- **Agente Senior Todoterreno**: Una única IA centralizada que planifica, inspecciona, programa y testea, evitando los mareos y fallos comunes de los sistemas multi-agente en modelos locales pequeños.
- **Memoria de Conversación**: El sistema recuerda el contexto de la charla en un historial dinámico, permitiéndote pedirle modificaciones incrementales como si hablaras con un compañero de trabajo.
- **Parches Anti-Fallos**: Un sistema de seguridad riguroso que atrapa el código generado (incluso si el modelo LLM tiene "alucinaciones" con el formato JSON o usa variables incorrectas como `"codigo"`) y crea las carpetas/archivos necesarios automáticamente.
- **Set de Herramientas Premium**: Dotado con 9 herramientas para interactuar con tu PC de forma autónoma.

---

## 🛠️ Capacidades de tu Agente Todoterreno

Gracias a sus parches de seguridad y su "System Prompt" blindado, tu agente es capaz de:
- **Escribir scripts desde cero:** Genera código en cualquier lenguaje y lo guarda automáticamente en tu disco duro.
- **Crear entornos complejos (Ej. Django / Node):** A través de nuestro exclusivo Parche de Emergencia de Terminal (Regex), el agente lanza comandos nativos como `django-admin startproject` de forma infalible, incluso si el LLM "alucina" con los formatos JSON.
- **Leer e inspeccionar código:** Puede abrir archivos locales que ya tengas escritos para buscar errores o proponer mejoras.
- **Desarrollo iterativo (Memoria):** Recuerda de qué habéis hablado. Puedes pedirle "Añade un formulario a la web que acabas de hacer" y mantendrá el hilo.
- **Supervivencia en 8GB de RAM:** Optimizado al extremo. En lugar de darle 9 herramientas que colapsan su razonamiento, le hemos dejado las 3 imprescindibles (`Terminal`, `Escritor` y `Lector`) para que sea un cirujano preciso con un modelo de solo 7B parámetros.

---

## 📚 Librerías y su Función

El "cerebro" de este agente está construido con las siguientes herramientas y dependencias de Python:

### Frameworks de Inteligencia Artificial
* **`crewai`** *(Agent, Task, Crew, Process, tool)*: Es la columna vertebral del proyecto. Define la "personalidad" del agente programador y le asigna la tarea principal con su caja de herramientas.
* **`langchain_community.tools`** *(DuckDuckGoSearchRun)*: Permite al agente salir a Internet a buscar respuestas a través del buscador DuckDuckGo (Herramienta `Buscador_Internet`).
* **`langchain_experimental.tools`** *(PythonREPLTool)*: Le da al agente una "consola interna" donde puede ejecutar código Python que él mismo acaba de escribir para ver si funciona (Herramienta `Ejecutor_Python`).

### Interfaz y Experiencia de Usuario (UX)
* **`threading`, `time`, `sys`**: Se utilizan en conjunto para crear la animación del spinner (`[2/3] 👩‍💻 Programador trabajando...`) y el cronómetro en tiempo real. Ejecutan la animación en un hilo paralelo (Background) para no bloquear el procesamiento del modelo de IA.
* **`logging`**: Silencia los fallos internos de la IA y los errores del "parche de seguridad", guardándolos discretamente en un archivo `agent_errors.log` para que tu terminal se mantenga súper limpia.
* **`dotenv`**: Carga de forma segura variables de entorno (como configuraciones extra o claves API, si decidieras usarlas en el futuro) desde un archivo `.env` oculto.

### Herramientas de Interacción con tu Ordenador (Librerías Core de Python)
* **`os`**: Fundamental para interactuar con tu sistema. Se usa para crear carpetas automáticamente (`os.makedirs`), leer el contenido de directorios (`os.listdir` en la Herramienta `Listador_Carpetas`) y lanzar la descarga automática de modelos (`os.system("ollama pull")`).
* **`subprocess`**: La herramienta `Ejecutor_Terminal` usa esta librería para lanzar comandos reales en tu terminal de Windows/Linux (`pip install`, `git commit`, `docker-compose up`) y capturar lo que devuelven.
* **`urllib.request` y `re`**: Constituyen el `Lector_Paginas_Web`. En lugar de instalar dependencias pesadas como Beautiful Soup, se usa `urllib` para descargar el HTML de una web, y expresiones regulares (`re`) para limpiar las etiquetas y dejar solo el texto legible.
* **`json`**: Crítico para la comunicación. El agente LLM intenta llamar a las herramientas pasándoles JSONs. Si el formato viene roto o alucinado, el parche de seguridad de `agent_develop.py` utiliza esta librería y `re` para hacer *string slicing* y rescatar tu código.

---

## 🚀 Cómo Empezar

1. Asegúrate de tener instalado [Ollama](https://ollama.com/) en tu sistema.
2. Instala las dependencias:
   ```bash
   pip install crewai langchain-community langchain-experimental python-dotenv
   ```
3. Ejecuta el script:
   ```bash
   python agent_develop.py
   ```
4. El sistema comprobará si tienes el modelo `qwen2.5-coder:7b` instalado. De no ser así, lo descargará automáticamente (puede tardar unos minutos).
5. ¡Habla con tu agente a través de la consola y pídele que te cree un proyecto paso a paso!