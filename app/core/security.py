from Crypto.Cipher import AES

def pad(text: bytes) -> bytes:
    padding = AES.block_size - len(text) % AES.block_size
    return text + bytes([padding] * padding)

def encrypt_aes(key: bytes, iv: bytes, data: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data))