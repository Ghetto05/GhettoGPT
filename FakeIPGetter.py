import hashlib


def generate_public_ipv4(number_int):
    number_str = str(number_int)

    # Hash the input to create a consistent base, avoiding sensitive IPs
    hash_bytes = hashlib.sha256(number_str.encode()).digest()

    def get_octet(byte_val, forbidden_ranges):
        # Map the byte (0-255) into a valid public range not in forbidden
        for _ in range(256):
            val = byte_val
            if all(not (r[0] <= val <= r[1]) for r in forbidden_ranges):
                return val
            byte_val = (byte_val + 1) % 256
        raise ValueError("Couldn't find valid public octet")

    # RFC1918 + Reserved ranges to avoid
    reserved_ranges = [
        (0, 0),           # "This" network
        (10, 10),         # Private
        (100, 100),       # Carrier-grade NAT
        (127, 127),       # Loopback
        (169, 169),       # Link-local
        (172, 172),       # 172.16.0.0 – 172.31.255.255 is private
        (192, 192),       # 192.168.x.x is private
        (198, 198),       # Some are reserved
        (224, 255),       # Multicast + reserved
    ]

    first_octet = get_octet(hash_bytes[0], reserved_ranges)

    # Other octets: we allow more freedom but avoid 0 and 255
    other_octets = [max(1, min(254, hash_bytes[i])) for i in range(1, 4)]

    ip_address = f"{first_octet}.{other_octets[0]}.{other_octets[1]}.{other_octets[2]}"
    return ip_address