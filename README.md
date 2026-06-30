# 🤖 Agents AI — Tu Desarrollador Autónomo Local

Agente de desarrollo de software que combina un **modelo local vía Ollama** con **Gemini como respaldo en la nube**. Ejecuta código, crea ficheros y usa la terminal de forma autónoma. Todo dentro de tu máquina.

---

## ⚡ Inicio Rápido

```bash
# 1. Instalar dependencias Python
pip install crewai langchain-community langchain-experimental python-dotenv

# 2. Copiar configuración
cp .env.example .env   # edita si necesitas cambiar algo

# 3. Elegir cómo correr Ollama → ver sección "Opciones de despliegue"

# 4. Lanzar el agente
python agent_develop.py
```

---

## 🗂️ Estructura del Proyecto

```
Agents_AI/
├── agent_develop.py     # Agente principal (CrewAI + herramientas)
├── compose.yml          # Ollama en Podman (opción contenedor)
├── pull_model.sh        # Descarga el modelo al contenedor (primera vez)
├── .env                 # Tus claves y configuración (no se sube a git)
├── .env.example         # Plantilla de configuración
├── .gitignore
└── README.md
```

---

## 🚀 Opciones de Despliegue

### Opción A — Ollama instalado en el host *(más simple)*

1. Instala Ollama desde [ollama.com](https://ollama.com)
2. Descarga el modelo:
   ```bash
   ollama pull llama3.1:8b
   ```
3. Lanza el agente:
   ```bash
   python agent_develop.py
   ```

No requiere ningún fichero extra. El agente detecta `ollama` en el PATH y tira automáticamente.

---

### Opción B — Ollama en contenedor Podman *(recomendado en producción)*

Ollama corre aislado en Podman. El agente Python corre en el host y se comunica con él por red.

```bash
# 1. Levantar el contenedor
podman-compose up -d

# 2. Descargar el modelo (solo la primera vez, ~4.7 GB)
bash pull_model.sh

# 3. Verificar que responde
curl http://localhost:11434/api/tags

# 4. Lanzar el agente
python agent_develop.py
```

El modelo se guarda en el volumen `ollama_data` — no se pierde al reiniciar el contenedor.

**Para parar Ollama:**
```bash
podman-compose down
```

**Para usar Docker en lugar de Podman:**  
Sustituye `podman-compose` por `docker compose` — el `compose.yml` es compatible con ambos.

---

## 🧠 Modelos disponibles

| Modelo | RAM necesaria | Velocidad | Calidad | Recomendado para |
|--------|--------------|-----------|---------|-----------------|
| `llama3.1:8b` | ~5 GB | Rápido | ★★★★☆ | **Uso general — opción por defecto** |
| `qwen2.5-coder:7b` | ~4.5 GB | Rápido | ★★★★☆ | Código puro, sin agentes complejos |
| `qwen2.5-coder:14b` | ~9 GB | Medio | ★★★★★ | Solo si tienes >16 GB libres |
| `gemma2:9b` | ~6 GB | Medio | ★★★★☆ | Alternativa sólida |
| `llama3.2:3b` | ~2.5 GB | Muy rápido | ★★★☆☆ | Máquinas con poca RAM |

**¿Por qué `llama3.1:8b` y no `qwen2.5-coder`?**  
El agente usa CrewAI que exige un formato estructurado `Thought/Action/Action Input`. `llama3.1:8b` sigue ese formato con mucha más fiabilidad, lo que reduce errores y activa menos el Safety Patch de emergencia.

Para cambiar el modelo edita la línea 162 de `agent_develop.py`:
```python
llm_model = 'ollama/llama3.1:8b'   # ← cambia aquí
```

---

## 🔑 Configuración (`.env`)

Copia `.env.example` a `.env` y ajusta los valores:

```bash
# URL del servidor Ollama
# - Ollama en host local → http://localhost:11434  (por defecto)
# - Ollama en otro servidor → http://IP:11434
OLLAMA_API_BASE=http://localhost:11434

# Gemini — respaldo automático cuando Ollama falla
# Obtén tu key gratuita en: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=tu_api_key_aqui
```

> `.env` está en `.gitignore`. Nunca se sube a git.

---

## 🔀 Fallback a Gemini

Cuando Ollama falla (timeout, error de memoria, tarea demasiado compleja), el agente escala automáticamente a **Gemini 2.0 Flash** sin que tengas que hacer nada:

```
Tú: "crea una API REST completa con autenticación JWT"
   ↓
🦙 Ollama intenta resolverlo
   ↓ (si falla)
⚠️ Ollama falló. Escalando a Gemini...
   ↓
✨ Gemini lo resuelve
   ↓
--- RESPUESTA [GEMINI ✨] ---
```

Si no configuras `GEMINI_API_KEY`, el agente simplemente muestra el error de Ollama y sigue funcionando con normalidad. El fallback es opcional.

Al arrancar verás el estado:
```
🤖 AGENTE INICIADO
   🦙 Principal : llama3.1:8b (Ollama local)
   ✅ Gemini 2.0 Flash configurado como respaldo
```

---

## 💻 Integración con VS Code

### Opción 1 — VS Code Task *(tu agente completo, recomendada)*

Crea `.vscode/tasks.json` en la carpeta del proyecto:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Lanzar Agente IA",
      "type": "shell",
      "command": "python agent_develop.py",
      "options": { "cwd": "${workspaceFolder}" },
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "focus": true
      },
      "group": { "kind": "build", "isDefault": true }
    }
  ]
}
```

Lanzar con `Ctrl+Shift+B`. El agente abre en el terminal integrado de VS Code con todas sus herramientas activas (CrewAI, Gemini fallback, historial de conversación).

### Opción 2 — Continue.dev *(chat en sidebar, sin herramientas)*

Instala la extensión [Continue](https://marketplace.visualstudio.com/items?itemName=Continue.continue) desde el marketplace.

Configura `~/.continue/config.yaml`:
```yaml
models:
  - name: llama3.1:8b (local)
    provider: ollama
    model: llama3.1:8b
    apiBase: http://localhost:11434
```

**Ventaja**: chat inline, autocompletado, contexto del fichero abierto.  
**Limitación**: conecta a Ollama directamente — no usa CrewAI ni el fallback a Gemini.

---

## 🎮 Herramientas del Agente

El agente tiene 9 herramientas disponibles. Por defecto solo 3 están activas (las más estables con modelos 7-8B):

| Herramienta | Estado | Descripción |
|------------|--------|-------------|
| `escritor_archivos` | ✅ Activa | Crea y sobreescribe ficheros |
| `lector_archivos` | ✅ Activa | Lee el contenido de ficheros |
| `ejecutor_terminal` | ✅ Activa | Ejecuta comandos de shell |
| `busqueda_internet` | ⚪ Disponible | Busca en DuckDuckGo |
| `ejecutor_python` | ⚪ Disponible | Ejecuta Python en sandbox |
| `preguntar_usuario` | ⚪ Disponible | El agente te hace preguntas |
| `listador_carpetas` | ⚪ Disponible | Lista directorios |
| `reemplazar_en_archivo` | ⚪ Disponible | Reemplaza texto en ficheros |
| `lector_web` | ⚪ Disponible | Lee páginas web |

Para activar herramientas adicionales, añádelas a `mis_herramientas` en `agent_develop.py` (línea 150).

---

## 🖥️ Requisitos de Hardware

| Componente | Mínimo | Recomendado |
|-----------|--------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 núcleos | 6+ núcleos |
| GPU | No necesaria | AMD/NVIDIA (acelera x5-x10) |
| Disco | 10 GB libres | 20 GB libres |

**Nota sobre GPU en Linux (Ryzen 4300GE / Radeon Vega iGPU):**

| Acción | Impacto | Dificultad |
|--------|---------|-----------|
| Subir UMA Frame Buffer a 2 GB en BIOS | ~40-50% más velocidad | BIOS solamente |
| Activar GPU en compose.yml (ya hecho) | ~10-15% con 512 MB VRAM | Configurado |
| GPU discreta NVIDIA/AMD | x5-x10 más velocidad | Hardware |

**Para activar la GPU en Podman** (ya configurado en `compose.yml`):
```bash
podman-compose down && podman-compose up -d   # reinicia con la nueva config
```
Ollama intentará usar ROCm/Vulkan con la iGPU. Verifica en los logs:
```bash
podman logs ollama | grep -i "gpu\|rocm\|vulkan"
```
Si no aparece nada de GPU, el iGPU Renoir no es compatible con ROCm — sigue funcionando en CPU.

**Para maximizar el rendimiento sin GPU discreta:**
1. En BIOS → `Advanced → AMD CBS → GFX Configuration → UMA Frame Buffer Size` → selecciona **2048 MB**
2. Reinicia y vuelve a levantar el contenedor

---

## 📦 Dependencias Python

```bash
pip install crewai langchain-community langchain-experimental python-dotenv
```

| Paquete | Para qué sirve |
|---------|---------------|
| `crewai` | Orquestación del agente, tareas y herramientas |
| `langchain-community` | Herramienta de búsqueda DuckDuckGo |
| `langchain-experimental` | Sandbox de ejecución Python |
| `python-dotenv` | Carga de variables desde `.env` |

---

## 📝 Comandos de uso

```
salir / exit / quit    → Cierra el agente
```

Cualquier otra cosa que escribas se envía al agente como tarea.

**Ejemplos:**
```
👤 Tú: crea un script Python que lea un CSV y genere un gráfico con matplotlib
👤 Tú: ahora añade un título al gráfico con el nombre del fichero
👤 Tú: instala las dependencias necesarias
```

---

## 🐛 Solución de Problemas

**El agente dice "Ollama falló" constantemente**  
→ Verifica que el contenedor Podman esté corriendo: `podman ps`  
→ Prueba la conexión: `curl http://localhost:11434/api/tags`  
→ Añade `GEMINI_API_KEY` en `.env` para activar el respaldo

**El modelo no está descargado**  
→ `bash pull_model.sh` (si usas Podman) o `ollama pull llama3.1:8b` (si usas Ollama en host)

**Errores de formato JSON / el agente no usa las herramientas bien**  
→ Los detalles se guardan en `agent_errors.log`  
→ Prueba con una instrucción más concreta y paso a paso

**Memoria insuficiente**  
→ Prueba un modelo más pequeño: `llama3.2:3b` (~2.5 GB RAM)
