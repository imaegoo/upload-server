import email
import email.policy
import html
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIR = r"D:\iMaeGoo\Downloads"
PORT = 8888


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return "%.1f %s" % (n, unit) if unit != "B" else "%d %s" % (n, unit)
        n /= 1024.0


def render_index():
    try:
        names = sorted(os.listdir(DIR))
    except OSError:
        names = []
    items = []
    for name in names:
        path = os.path.join(DIR, name)
        if not os.path.isfile(path):
            continue
        try:
            size = human_size(os.path.getsize(path))
        except OSError:
            size = "-"
        href = "/files/" + urllib.parse.quote(name)
        items.append(
            "<li><a href=\"%s\">%s</a> (%s)</li>"
            % (href, html.escape(name), size)
        )
    listing = "\n".join(items) if items else "<li>（空）</li>"
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>文件服务</title>\n</head>\n<body>\n"
        "<h3>上传文件</h3>\n"
        "<form action=\"/upload\" method=\"post\" enctype=\"multipart/form-data\">\n"
        "<input type=\"file\" name=\"file\" required>\n"
        "<button type=\"submit\">上传</button>\n"
        "</form>\n"
        "<h3>文件列表</h3>\n"
        "<ul>\n" + listing + "\n</ul>\n"
        "</body>\n</html>\n"
    ).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "SimpleUpload/1.0"

    def _send(self, code, body, content_type="text/html; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._send(200, render_index())
        elif path.startswith("/files/"):
            self._serve_file(path[len("/files/"):])
        else:
            self._send(404, b"<h3>404 Not Found</h3>")

    def do_HEAD(self):
        self.do_GET()

    def _serve_file(self, raw_name):
        name = os.path.basename(urllib.parse.unquote(raw_name))
        target = os.path.join(DIR, name)
        if not name or not os.path.isfile(target):
            self._send(404, b"<h3>404 Not Found</h3>")
            return
        size = os.path.getsize(target)
        quoted = urllib.parse.quote(name)
        extra = {
            "Content-Disposition": "attachment; filename=\"%s\"; filename*=UTF-8''%s"
            % (quoted, quoted)
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(target, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/upload":
            self._send(404, b"<h3>404 Not Found</h3>")
            return
        length = int(self.headers.get("Content-Length") or 0)
        ctype = self.headers.get("Content-Type") or ""
        if length <= 0 or "multipart/form-data" not in ctype:
            self._send(400, b"<h3>400 Bad Request</h3>")
            return
        body = self.rfile.read(length)
        msg = email.parser.BytesParser(policy=email.policy.default).parsebytes(
            ("Content-Type: %s\r\nMIME-Version: 1.0\r\n\r\n" % ctype).encode("utf-8")
            + body
        )
        saved = []
        for part in msg.iter_parts():
            filename = part.get_filename()
            if not filename:
                continue
            filename = os.path.basename(filename)
            data = part.get_payload(decode=True) or b""
            target = os.path.join(DIR, filename)
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(target):
                target = os.path.join(DIR, "%s_%d%s" % (base, i, ext))
                i += 1
            with open(target, "wb") as f:
                f.write(data)
            saved.append(os.path.basename(target))
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    os.makedirs(DIR, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("Serving %s on http://0.0.0.0:%d/" % (DIR, PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
