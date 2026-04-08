import secrets

def generate_reference():
    return "tx_" + secrets.token_hex(8)