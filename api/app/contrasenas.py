"""Hash de contraseñas de administradores con scrypt (biblioteca estándar de Python).

scrypt es lento a propósito y usa mucha memoria: así, aunque alguien robara la base
de datos, probar millones de contraseñas sería muy costoso. Cada contraseña lleva
una "sal" aleatoria, por lo que dos contraseñas iguales producen hashes distintos.
"""

import hashlib
import hmac
import secrets

# Parámetros de costo (n = 2^14, r = 8, p = 1 usa ~16 MB por cálculo)
COSTO_N = 2**14
BLOQUE_R = 8
PARALELISMO_P = 1
LONGITUD_HASH = 32
LONGITUD_MINIMA = 10


def _calcular(contrasena: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        contrasena.encode("utf-8"), salt=sal, n=n, r=r, p=p, dklen=LONGITUD_HASH, maxmem=64 * 1024 * 1024
    )


def generar_hash(contrasena: str) -> str:
    """Devuelve el texto a guardar en la base: algoritmo, parámetros, sal y hash."""
    if len(contrasena) < LONGITUD_MINIMA:
        raise ValueError(f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres.")
    sal = secrets.token_bytes(16)
    resultado = _calcular(contrasena, sal, COSTO_N, BLOQUE_R, PARALELISMO_P)
    return f"scrypt${COSTO_N}${BLOQUE_R}${PARALELISMO_P}${sal.hex()}${resultado.hex()}"


def verificar(contrasena: str, hash_guardado: str) -> bool:
    """Comprueba una contraseña contra el hash guardado (comparación en tiempo constante)."""
    try:
        algoritmo, n, r, p, sal, esperado = hash_guardado.split("$")
        if algoritmo != "scrypt":
            return False
        calculado = _calcular(contrasena, bytes.fromhex(sal), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculado.hex(), esperado)


# Hash de una contraseña aleatoria: se usa cuando el usuario no existe, para que la
# respuesta tarde lo mismo y no revele qué usuarios existen.
HASH_FICTICIO = generar_hash(secrets.token_urlsafe(16))
