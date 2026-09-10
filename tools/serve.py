#!/usr/bin/env python3
"""Static website preview with single-range MP4 requests for reliable seeking."""
import argparse
import os
from pathlib import Path
import re
import shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        path = self.translate_path(self.path)
        if not path.lower().endswith('.mp4') or not os.path.isfile(path):
            return super().send_head()
        try:
            stream = open(path, 'rb')
        except OSError:
            self.send_error(404)
            return None
        size = os.fstat(stream.fileno()).st_size
        start, end = 0, size - 1
        requested = self.headers.get('Range')
        if requested:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested.strip())
            valid = bool(match and any(match.groups()))
            if valid:
                first, last = match.groups()
                if first:
                    start = int(first)
                    end = min(int(last), end) if last else end
                else:
                    start = max(0, size - int(last))
                valid = start <= end and start < size
            if not valid:
                stream.close()
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return None
        self.send_response(206 if requested else 200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if requested:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        stream.seek(start)
        self.remaining = end - start + 1
        return stream

    def copyfile(self, source, outputfile):
        try:
            if self.remaining is None:
                shutil.copyfileobj(source, outputfile)
            else:
                while self.remaining:
                    block = source.read(min(self.remaining, 64 * 1024))
                    if not block:
                        break
                    outputfile.write(block)
                    self.remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Browsers cancel outstanding downloads when seeking.


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8899)
    parser.add_argument('--bind', default='127.0.0.1')
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parents[1])
    with ThreadingHTTPServer((args.bind, args.port), Handler) as server:
        print(f'Preview: http://{args.bind}:{args.port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
