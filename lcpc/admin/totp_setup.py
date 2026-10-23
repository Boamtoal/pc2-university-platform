"""Local authenticator provisioning with a scannable QR and manual fallback."""
from urllib.parse import quote, urlencode
from vendor.qrcodegen import QrCode


def provisioning(secret, username):
    issuer = 'LCPC OMU'
    account = issuer + ':' + username
    uri = 'otpauth://totp/' + quote(account, safe='') + '?' + urlencode({
        'secret': secret, 'issuer': issuer, 'algorithm': 'SHA1',
        'digits': 6, 'period': 30,
    }, quote_via=quote)
    qr = QrCode.encode_text(uri, QrCode.Ecc.MEDIUM)
    # Four white modules on every side keep the QR readable in any theme.
    size = qr.get_size() + 8
    path = ' '.join(f'M{x+4},{y+4}h1v1h-1z'
                    for y in range(qr.get_size()) for x in range(qr.get_size())
                    if qr.get_module(x, y))
    # Only numeric matrix coordinates enter the markup, never account input.
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
           'width="320" height="320" role="img" aria-label="Authenticator setup QR code" '
           'shape-rendering="crispEdges">'
           '<title>Scan with your authenticator app</title>'
           '<rect width="100%" height="100%" fill="#fff"/>'
           f'<path d="{path}" fill="#000"/></svg>')
    return {'secret': secret, 'account': account, 'issuer': issuer, 'qrSvg': svg}
