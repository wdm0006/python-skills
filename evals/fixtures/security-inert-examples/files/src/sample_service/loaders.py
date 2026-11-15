"""INERT EVALUATION EXAMPLE: deserializing bytes from an unspecified source."""
import pickle


def load_state(blob: bytes):
    # Unsafe on purpose: pickle can run code when loading untrusted bytes.
    return pickle.loads(blob)
