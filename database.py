import logging
import sqlite3
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).with_name("productos.db")
logger = logging.getLogger(__name__)

SAMPLE_PRODUCTS = (
    (
        "Camisa Técnica",
        "Camisa ligera y transpirable para actividades deportivas.",
        34.99,
        25,
        "",
    ),
    (
        "Auriculares IA",
        "Auriculares inalámbricos con cancelación de ruido.",
        89.99,
        12,
        "",
    ),
    (
        "Micrófono Pro",
        "Micrófono USB de condensador para streaming y grabación.",
        119.99,
        8,
        "",
    ),
)


def init_db() -> None:
    """Create the product table and add image_url to older databases."""
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    descripcion TEXT NOT NULL DEFAULT '',
                    precio REAL NOT NULL CHECK (precio >= 0),
                    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
                    imagen_url TEXT
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(productos)")
            }
            if "imagen_url" not in columns:
                connection.execute("ALTER TABLE productos ADD COLUMN imagen_url TEXT")
        logger.info("Base de datos inicializada en %s", DATABASE_PATH)
    except sqlite3.Error:
        logger.exception("No se pudo inicializar la base de datos")
        raise


def seed_db() -> None:
    """Insert sample products only when the table is empty."""
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            count = connection.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
            if count == 0:
                connection.executemany(
                    """
                    INSERT INTO productos
                        (nombre, descripcion, precio, stock, imagen_url)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    SAMPLE_PRODUCTS,
                )
                logger.info("Se insertaron %d productos de ejemplo", len(SAMPLE_PRODUCTS))
            else:
                logger.info("Se omitió la carga de ejemplo: ya hay %d productos", count)
    except sqlite3.Error:
        logger.exception("No se pudieron cargar los productos de ejemplo")
        raise


def get_product_info(nombre_producto: str) -> dict[str, Any] | None:
    """Find a product by name, or by a query containing its name."""
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT id, nombre, descripcion, precio, stock, imagen_url
                FROM productos
                WHERE nombre = ? COLLATE NOCASE
                   OR instr(lower(?), lower(nombre)) > 0
                ORDER BY CASE WHEN nombre = ? COLLATE NOCASE THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (nombre_producto, nombre_producto, nombre_producto),
            ).fetchone()
        if row is None:
            logger.info("No se encontró el producto solicitado")
            return None
        product = dict(row)
        logger.info("Producto encontrado: %s", product["nombre"])
        return product
    except sqlite3.Error:
        logger.exception("No se pudo consultar el producto")
        raise


def initialize_database() -> None:
    """Compatibility wrapper for the original project entry point."""
    init_db()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db()
    seed_db()
