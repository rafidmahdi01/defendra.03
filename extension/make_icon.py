from pathlib import Path
import zlib
import struct

for size in (48, 128):
    w = h = size
    rows = [b'\x00' + b''.join(bytes((20, 160 + (x * 80 // (w - 1)), 40, 255)) for x in range(w)) for _ in range(h)]
    raw = b''.join(rows)
    png = b'\x89PNG\r\n\x1a\n'

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t, zlib.crc32(d)) & 0xffffffff)

    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw))
    png += chunk(b'IEND', b'')
    Path(f'icon{size}.png').write_bytes(png)
    print(f'icon{size}.png created')
