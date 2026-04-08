import secrets

def generate_public_key():
    return "pk_test_" + secrets.token_hex(16)

def generate_secret_key():
    return "sk_test_" + secrets.token_hex(32)