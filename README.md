# 🎙️ AI Streamer Avatar - Orquestador de Presentador Virtual

Sistema modular en Python para generar un avatar digital interactivo en tiempo real, diseñado para transmisiones en vivo (streaming) a través de OBS Studio. Integra Inteligencia Artificial (LLM), Síntesis de Voz realista y Animación Facial a partir de una base de datos de productos.

---

## 🏗️ Arquitectura del Flujo

1. **Entrada**: El usuario o un script de chat envía una pregunta sobre un producto.
2. **Base de Datos (RAG)**: Se consulta la información real del producto (nombre, precio, stock) para evitar alucinaciones del modelo.
3. **El Cerebro (OpenAI GPT-4o)**: Genera una respuesta natural y persuasiva basada en el contexto de la BD.
4. **La Voz (ElevenLabs)**: Convierte la respuesta de texto en un archivo de audio realista.
5. **La Cara (D-ID)**: Anima una imagen estática (avatar) sincronizándola con el audio generado.
6. **Salida (OBS Studio)**: El video resultante se inyecta automáticamente en la transmisión en vivo.

---

## 📂 Estructura del Proyecto

```text
ai-streamer-avatar/
│
├── .env                     # Variables de entorno (API Keys) - ¡NO SUBIR A GIT!
├── requirements.txt         # Dependencias de Python
├── main.py                  # Script orquestador principal
├── database.py              # Lógica de conexión y consulta a la BD
├── productos.db             # Base de datos SQLite (se genera automáticamente)
├── obs_controller.py        # Integración con OBS Studio vía WebSocket
└── assets/
    ├── avatar.png           # Imagen base del avatar (rostro)
    └── latest_video.mp4     # Archivo temporal donde se guarda el video generado
```

## ⚙️ Configuración y ejecución

1. Crea un entorno virtual con `python3 -m venv .venv`, actívalo con
   `source .venv/bin/activate` e instala dependencias con
   `python -m pip install -r requirements.txt`.
2. Copia `.env.example` como `.env` y completa las claves de OpenAI, ElevenLabs
   y D-ID. Configura también
   `D_ID_AVATAR_URL` con una URL pública y accesible por D-ID para la imagen del
   avatar; una ruta local como `assets/avatar.png` no es accesible desde su API.
3. En OBS, activa WebSocket (puerto `4455` por defecto), configura su contraseña
   en `OBS_WS_PASSWORD` y crea una fuente de medios llamada `AvatarAI`.
4. Ejecuta `python main.py` desde el entorno virtual. La base de datos se crea y
   carga con productos de ejemplo la primera vez. Escribe `salir` para detener
   el programa.

El audio de ElevenLabs se guarda localmente en `assets/audio_output.mp3`. Como
D-ID no puede acceder a ese archivo local, genera la voz del video con su
proveedor integrado de ElevenLabs. `D_ID_API_KEY` debe contener la credencial
Basic proporcionada por D-ID.