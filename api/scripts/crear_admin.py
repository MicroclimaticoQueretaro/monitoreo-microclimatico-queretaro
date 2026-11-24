"""Crea (o cambia la contraseña de) una cuenta de administrador.

Uso (desde la carpeta api/):
    python -m scripts.crear_admin malu

La contraseña se pide sin mostrarse en pantalla y nunca se guarda: solo su hash.
"""

import getpass
import sys

from sqlalchemy import text

from app.contrasenas import LONGITUD_MINIMA, generar_hash
from app.db import obtener_motor


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m scripts.crear_admin <usuario>")
    usuario = sys.argv[1].lower()

    contrasena = getpass.getpass(f"Contraseña para '{usuario}' (mínimo {LONGITUD_MINIMA} caracteres): ")
    if contrasena != getpass.getpass("Repita la contraseña: "):
        sys.exit("Error: las contraseñas no coinciden.")
    try:
        hash_contrasena = generar_hash(contrasena)
    except ValueError as error:
        sys.exit(f"Error: {error}")

    with obtener_motor().begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO administradores (usuario, hash_contrasena) VALUES (:u, :h) "
                "ON CONFLICT (usuario) DO UPDATE SET hash_contrasena = EXCLUDED.hash_contrasena, activo = TRUE"
            ),
            {"u": usuario, "h": hash_contrasena},
        )
        # Por seguridad, al cambiar la contraseña se cierran las sesiones abiertas
        conexion.execute(
            text("DELETE FROM sesiones_admin WHERE administrador_id = (SELECT id FROM administradores WHERE usuario = :u)"),
            {"u": usuario},
        )
    print(f"Administrador '{usuario}' listo.")


if __name__ == "__main__":
    main()
