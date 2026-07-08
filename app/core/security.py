from pwdlib import PasswordHash


# Hash moderno recomendado para contraseñas.
# Evita guardar contraseñas en texto plano.
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Genera un hash seguro para una contraseña.
    """
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash.
    """
    return password_hash.verify(password, hashed_password)