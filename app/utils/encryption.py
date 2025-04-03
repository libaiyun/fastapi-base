import base64
import hashlib
import os

from cryptography.fernet import Fernet

from app.config import config

# 推荐通过环境变量注入密钥
# 生成新密钥：Fernet.generate_key().decode()
# 定期轮换密钥时需要迁移历史数据
cipher_suite = Fernet(config.encryption_key)


def encrypt_value(v: str) -> str:
    """将明文加密为Base64字符串"""
    encrypted_bytes = cipher_suite.encrypt(v.encode())
    return base64.urlsafe_b64encode(encrypted_bytes).decode()


def decrypt_value(v: str, raise_exc=True) -> str:
    """将Base64字符串解密为明文"""
    try:
        encrypted_bytes = base64.urlsafe_b64decode(v.encode())
        return cipher_suite.decrypt(encrypted_bytes).decode()
    except Exception:
        if raise_exc:
            raise
        else:
            return v


def safe_decrypt_value(v: str) -> str:
    return decrypt_value(v, raise_exc=False)


# 在加密前添加随机盐（防御模式识别）
def encrypt_with_salt(v: str) -> str:
    salt = os.urandom(16).hex()
    return encrypt_value(f"{salt}${v}")


# 解密时去除盐值
def decrypt_with_salt(v: str) -> str:
    decrypted = decrypt_value(v)
    return decrypted.split("$")[1]


# 哈希生成器
def sha256_hash(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()
