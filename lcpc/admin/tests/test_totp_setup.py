"""Decode the rendered QR with an independent scanner when OpenCV is available."""
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from totp_setup import provisioning

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None


class AuthenticatorQR(unittest.TestCase):
    secret = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'

    def test_markup_has_no_account_or_secret_interpolation(self):
        svg = provisioning(self.secret, '<script>alert(1)</script>')['qrSvg']
        self.assertNotIn('<script>', svg)
        self.assertNotIn(self.secret, svg)
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib['role'], 'img')
        self.assertEqual(root.find('{*}rect').attrib['fill'], '#fff')
        self.assertEqual(root.find('{*}path').attrib['fill'], '#000')

    @unittest.skipUnless(cv2 is not None, 'OpenCV is an optional independent QR decoder')
    def test_scan_recovers_exact_authenticator_settings(self):
        for username in ('admin', 'owner_' + 'x' * 26):
            with self.subTest(username=username):
                setup = provisioning(self.secret, username)
                root = ET.fromstring(setup['qrSvg'])
                size = int(root.attrib['viewBox'].split()[-1])
                image = np.full((size, size), 255, dtype=np.uint8)
                for x, y in re.findall(r'M(\d+),(\d+)h1v1h-1z', root.find('{*}path').attrib['d']):
                    image[int(y), int(x)] = 0
                self.assertTrue(np.all(image[:4] == 255))
                self.assertTrue(np.all(image[-4:] == 255))
                self.assertTrue(np.all(image[:, :4] == 255))
                self.assertTrue(np.all(image[:, -4:] == 255))
                image = cv2.resize(image, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
                detector = cv2.QRCodeDetectorAruco() if hasattr(cv2, 'QRCodeDetectorAruco') else cv2.QRCodeDetector()
                payload, _, _ = detector.detectAndDecode(image)
                uri = urlsplit(payload)
                self.assertEqual((uri.scheme, uri.netloc), ('otpauth', 'totp'))
                self.assertEqual(unquote(uri.path), '/' + setup['account'])
                self.assertEqual(parse_qs(uri.query), {
                    'secret': [self.secret], 'issuer': ['LCPC OMU'],
                    'algorithm': ['SHA1'], 'digits': ['6'], 'period': ['30'],
                })


if __name__ == '__main__':
    unittest.main()
