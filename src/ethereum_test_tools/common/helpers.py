"""
Helper functions/classes used to generate Ethereum tests.
"""

from typing import List, SupportsBytes

from ethereum.crypto.hash import keccak256
from ethereum.rlp import encode

from .conversions import BytesConvertible, FixedSizeBytesConvertible
from .types import Address, Bytes, Hash

"""
Helper functions
"""


def ceiling_division(a: int, b: int) -> int:
    """
    Calculates the ceil without using floating point.
    Used by many of the EVM's formulas
    """
    return -(a // -b)


def compute_create_address(address: FixedSizeBytesConvertible, nonce: int) -> str:
    """
    Compute address of the resulting contract created using a transaction
    or the `CREATE` opcode.
    """
    nonce_bytes = bytes() if nonce == 0 else nonce.to_bytes(length=1, byteorder="big")
    hash = keccak256(encode([Address(address), nonce_bytes]))
    return "0x" + hash[-20:].hex()


def compute_create2_address(
    address: FixedSizeBytesConvertible, salt: FixedSizeBytesConvertible, initcode: BytesConvertible
) -> str:
    """
    Compute address of the resulting contract created using the `CREATE2`
    opcode.
    """
    hash = keccak256(b"\xff" + Address(address) + Hash(salt) + keccak256(Bytes(initcode)))
    return "0x" + hash[-20:].hex()


def cost_memory_bytes(new_bytes: int, previous_bytes: int) -> int:
    """
    Calculates the cost of memory expansion, based on the costs specified in
    the yellow paper: https://ethereum.github.io/yellowpaper/paper.pdf
    """
    if new_bytes <= previous_bytes:
        return 0
    new_words = ceiling_division(new_bytes, 32)
    previous_words = ceiling_division(previous_bytes, 32)

    def c(w: int) -> int:
        g_memory = 3
        return (g_memory * w) + ((w * w) // 512)

    return c(new_words) - c(previous_words)


def copy_opcode_cost(length: int) -> int:
    """
    Calculates the cost of the COPY opcodes, assuming memory expansion from
    empty memory, based on the costs specified in the yellow paper:
    https://ethereum.github.io/yellowpaper/paper.pdf
    """
    return 3 + (ceiling_division(length, 32) * 3) + cost_memory_bytes(length, 0)


def eip_2028_transaction_data_cost(data: BytesConvertible) -> int:
    """
    Calculates the cost of a given data as part of a transaction, based on the
    costs specified in EIP-2028: https://eips.ethereum.org/EIPS/eip-2028
    """
    cost = 0
    for b in Bytes(data):
        if b == 0:
            cost += 4
        else:
            cost += 16
    return cost


def to_address(input: FixedSizeBytesConvertible) -> str:
    """
    Converts an int or str into proper address 20-byte hex string.
    """
    return str(Address(input))


def to_hash_bytes(input: FixedSizeBytesConvertible) -> bytes:
    """
    Converts an int or str into proper 32-byte hash.
    """
    return bytes(Hash(input))


def to_hash(input: FixedSizeBytesConvertible) -> str:
    """
    Converts an int or str into proper 32-byte hash hex string.
    """
    return str(Hash(input))


def add_kzg_version(
    b_hashes: List[bytes | SupportsBytes | int | str], kzg_version: int
) -> List[bytes]:
    """
    Adds the Kzg Version to each blob hash.
    """
    kzg_version_hex = bytes([kzg_version])
    kzg_versioned_hashes = []

    for hash in b_hashes:
        if isinstance(hash, int) or isinstance(hash, str):
            kzg_versioned_hashes.append(kzg_version_hex + to_hash_bytes(hash)[1:])
        elif isinstance(hash, bytes) or isinstance(hash, SupportsBytes):
            if isinstance(hash, SupportsBytes):
                hash = bytes(hash)
            kzg_versioned_hashes.append(kzg_version_hex + hash[1:])
        else:
            raise TypeError("Blob hash must be either an integer, string or bytes")
    return kzg_versioned_hashes
