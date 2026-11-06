import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from obsws_python.error import OBSSDKError

from database import get_product_info, init_db, seed_db
from obs_controller import OBSController


load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).with_name("assets")
AUDIO_PATH = ASSETS_DIR / "audio_output.mp3"
VIDEO_PATH = ASSETS_DIR / "latest_video.mp4"
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obbf5AWCGJqNT0")
DID_API_BASE_URL = "https://api.d-id.com"


def generate_response(query: str) -> str:
    product = get_product_info(query)
    if product is None:
        raise ValueError("No encontré ese producto en la base de datos.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta configurar OPENAI_API_KEY en el archivo .env")

    client = OpenAI(api_key=api_key)
    context = (
        f"Nombre: {product['nombre']}\n"
        f"Descripción: {product['descripcion']}\n"
        f"Precio: ${product['precio']:.2f}\n"
        f"Stock: {product['stock']}"
    )
    try:
        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un embajador de marca amable y honesto. Responde en "
                        "español en un máximo de dos oraciones y usa únicamente los "
                        "datos del producto proporcionados. No inventes información."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Consulta: {query}\n\nDatos del producto:\n{context}",
                },
            ],
            max_tokens=160,
        )
        response = result.choices[0].message.content
        if not response:
            raise RuntimeError("OpenAI devolvió una respuesta vacía")
        sentences = re.split(r"(?<=[.!?])\s+", response.strip())
        return " ".join(sentences[:2])
    except Exception:
        logger.exception("No se pudo generar la respuesta con OpenAI")
        raise


def text_to_speech(text: str) -> str:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("Falta configurar ELEVENLABS_API_KEY en el archivo .env")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        AUDIO_PATH.write_bytes(response.content)
        logger.info("Audio guardado en %s", AUDIO_PATH)
        return str(AUDIO_PATH)
    except requests.RequestException:
        logger.exception("Falló la solicitud de síntesis de voz a ElevenLabs")
        raise
    except OSError:
        logger.exception("No se pudo guardar el audio")
        raise


def _did_headers() -> dict[str, str]:
    api_key = os.getenv("D_ID_API_KEY") or os.getenv("DID_API_KEY")
    if not api_key:
        raise RuntimeError("Falta configurar D_ID_API_KEY en el archivo .env")
    return {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def animate_avatar(
    audio_path: str, image_url: str, text: str | None = None
) -> str:
    """Create a D-ID video; D-ID must receive a public image URL.

    The local audio file is retained as a generated asset. Since D-ID cannot fetch
    a local path, its ElevenLabs provider synthesizes the same text for the video.
    """
    audio_file = Path(audio_path)
    if not audio_file.is_file():
        raise FileNotFoundError(f"No existe el archivo de audio: {audio_file}")
    if not image_url.startswith(("https://", "http://")):
        raise ValueError("D-ID requiere una URL pública para la imagen del avatar.")
    if not text:
        raise ValueError("Se necesita el texto para sincronizar la voz del avatar.")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obbf5AWCGJqNT0")
    payload = {
        "source_url": image_url,
        "script": {
            "type": "text",
            "input": text,
            "provider": {
                "type": "elevenlabs",
                "voice_id": voice_id,
                "voice_model": "eleven_multilingual_v2",
            },
        },
    }

    try:
        response = requests.post(
            f"{DID_API_BASE_URL}/talks",
            headers=_did_headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        talk_id = response.json().get("id")
        if not talk_id:
            raise RuntimeError("D-ID no devolvió el identificador de la animación")

        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            time.sleep(3)
            status_response = requests.get(
                f"{DID_API_BASE_URL}/talks/{talk_id}",
                headers=_did_headers(),
                timeout=30,
            )
            status_response.raise_for_status()
            result = status_response.json()
            status = result.get("status")
            if status == "done":
                result_url = result.get("result_url")
                if not result_url:
                    raise RuntimeError("D-ID terminó sin devolver la URL del video")
                video_response = requests.get(result_url, timeout=60, stream=True)
                video_response.raise_for_status()
                ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                with VIDEO_PATH.open("wb") as video_file:
                    for chunk in video_response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            video_file.write(chunk)
                logger.info("Video de avatar guardado en %s", VIDEO_PATH)
                return str(VIDEO_PATH)
            if status == "error":
                raise RuntimeError(
                    f"D-ID no pudo generar el video: {result.get('error', result)}"
                )
        raise TimeoutError("D-ID no terminó la animación dentro de 10 minutos")
    except requests.RequestException:
        logger.exception("Falló la solicitud de animación a D-ID")
        raise
    except OSError:
        logger.exception("No se pudo guardar el video del avatar")
        raise


def main() -> None:
    init_db()
    seed_db()

    obs = OBSController()
    try:
        obs.connect()
        while True:
            try:
                query = input("\n¿Qué producto quieres consultar? (escribe 'salir' para terminar): ")
                if query.strip().casefold() in {"salir", "exit", "quit"}:
                    break
                if not query.strip():
                    continue

                answer = generate_response(query)
                audio_path = text_to_speech(answer)
                image_url = os.getenv("D_ID_AVATAR_URL", "")
                video_path = animate_avatar(audio_path, image_url, answer)
                obs.play_video(video_path)
                print(answer)
            except (
                OpenAIError,
                OBSSDKError,
                requests.RequestException,
                RuntimeError,
                ValueError,
                OSError,
            ) as exc:
                logger.error("No se pudo completar esta consulta: %s", exc)
                print(f"No se pudo completar la solicitud: {exc}")
    except Exception:
        logger.exception("No se pudo iniciar el flujo del avatar")
        raise
    finally:
        obs.disconnect()


if __name__ == "__main__":
    main()
