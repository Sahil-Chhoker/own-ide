from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

class Hasher:
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return password_hash.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return password_hash.hash(password)