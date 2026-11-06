import logging
import os
from pathlib import Path

import obsws_python


logger = logging.getLogger(__name__)


class OBSController:
    def __init__(self) -> None:
        self.host = os.getenv("OBS_WS_HOST", os.getenv("OBS_HOST", "localhost"))
        try:
            self.port = int(os.getenv("OBS_WS_PORT", os.getenv("OBS_PORT", "4455")))
        except ValueError as exc:
            raise ValueError("OBS_WS_PORT debe ser un número entero") from exc
        self.password = os.getenv(
            "OBS_WS_PASSWORD", os.getenv("OBS_PASSWORD", "")
        )
        self._client: obsws_python.ReqClient | None = None

    def connect(self) -> None:
        if self._client is not None:
            return
        try:
            self._client = obsws_python.ReqClient(
                host=self.host,
                port=self.port,
                password=self.password,
                timeout=5,
            )
            logger.info("Conectado a OBS en %s:%s", self.host, self.port)
        except Exception:
            logger.exception("No se pudo conectar a OBS en %s:%s", self.host, self.port)
            raise

    def play_video(
        self, file_path: str, source_name: str = "AvatarAI"
    ) -> None:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"No existe el video: {path}")
        if self._client is None:
            raise RuntimeError("OBS no está conectado; llama a connect() primero")
        try:
            self._client.set_input_settings(
                name=source_name,
                settings={"local_file": str(path), "is_local_file": True},
                overlay=True,
            )
            self._client.trigger_media_input_action(
                name=source_name,
                action="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART",
            )
            logger.info("Se inició el video %s en la fuente %s", path, source_name)
        except Exception:
            logger.exception("No se pudo reproducir el video en OBS")
            raise

    def disconnect(self) -> None:
        if self._client is None:
            return
        client, self._client = self._client, None
        try:
            client.disconnect()
            logger.info("Desconectado de OBS")
        except Exception:
            logger.exception("No se pudo cerrar correctamente la conexión con OBS")
            raise
