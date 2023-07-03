import inspect
import os

from django.test import TestCase
from wrapper import AWSKMSWrapper, FailWrapper, KMSWrapper


class WrapperTestCase(TestCase):
    def test_protocol(self):
        for cls in (FailWrapper, AWSKMSWrapper):
            with self.subTest(cls=cls):
                self.assertTrue(issubclass(cls, KMSWrapper))
                self.assertEqual(
                    inspect.signature(cls.encrypt),
                    inspect.signature(KMSWrapper.encrypt),
                )

    def test_fail_wrapper(self):
        wrapper = FailWrapper()
        with self.assertRaises(ValueError):
            wrapper.encrypt(b'')
        with self.assertRaises(ValueError):
            wrapper.decrypt(b'')

    def test_aws_kms(self):
        if 'AWSKMS_WRAPPER_KEY_ID' not in os.environ:
            self.skipTest("AWSKMS_WRAPPER_KEY_ID must be set to test this wrapper")

        wrapper = AWSKMSWrapper()
        for msg in (b'', b'test', b'hello'):
            with self.subTest(msg=msg):
                encrypted = wrapper.encrypt(msg)
                self.assertNotEqual(msg, encrypted)
                decrypted = wrapper.decrypt(encrypted)
                self.assertEqual(decrypted, msg)
