import boto3
import codecs
import os

from typing import Protocol, runtime_checkable


@runtime_checkable
class KMSWrapper(Protocol):
    def encrypt(self, plaintext: bytes) -> bytes:
        ...

    def decrypt(self, ciphertext: bytes) -> bytes:
        ...


class FailWrapper:
    def encrypt(self, plaintext: bytes) -> bytes:
        raise ValueError('No encryption wrapper has been configured')

    def decrypt(self, ciphertext: bytes) -> bytes:
        raise ValueError('No encryption wrapper has been configured')


class ROT13Wrapper:
    """ROT13Wrapper is used in the tests"""
    def encrypt(self, plaintext: bytes) -> bytes:
        return codecs.encode(plaintext.decode(), 'rot_13').encode()

    def decrypt(self, ciphertext: bytes) -> bytes:
        return codecs.encode(ciphertext.decode(), 'rot_13').encode()


class AWSKMSWrapper:
    def __init__(self) -> None:
        self.key_id = os.environ['AWSKMS_WRAPPER_KEY_ID']
        self.client = boto3.client(
            'kms',
            endpoint_url=os.environ.get('AWSKMS_ENDPOINT_URL'),
        )

    def encrypt(self, plaintext: bytes) -> bytes:
        response = self.client.encrypt(
            KeyId=self.key_id,
            Plaintext=plaintext,
        )
        return response['CiphertextBlob']

    def decrypt(self, ciphertext: bytes) -> bytes:
        response = self.client.decrypt(
            KeyId=self.key_id,
            CiphertextBlob=ciphertext,
        )
        return response['Plaintext']
