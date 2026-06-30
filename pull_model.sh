#!/bin/bash
# Espera a que el contenedor Ollama esté listo y descarga llama3.1:8b
echo "Esperando a que Ollama arranque..."
until podman exec ollama ollama list &>/dev/null; do
  echo "  ..."
  sleep 2
done
echo "Ollama listo. Descargando llama3.1:8b (~4.7 GB, solo la primera vez)..."
podman exec ollama ollama pull llama3.1:8b
echo "Modelo listo."
