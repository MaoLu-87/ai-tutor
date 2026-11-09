#!/usr/bin/env python
"""在本机启动刷题页的局域网服务。

双击「启动刷题.bat」即可，或命令行 python serve.py。
iPad 与电脑连同一个 WiFi，用下面打印的地址打开。
"""
import http.server
import os
import socket
import socketserver
import sys

PORT = 8000
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "publish")


def lan_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def main():
    if not os.path.isdir(ROOT):
        print("找不到 publish 目录，请先运行: python make_drill.py")
        sys.exit(1)

    os.chdir(ROOT)
    handler = http.server.SimpleHTTPRequestHandler

    class Quiet(handler):
        def log_message(self, fmt, *args):
            pass

    try:
        httpd = socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Quiet)
    except OSError:
        print(f"端口 {PORT} 被占用了。关掉别的窗口，或改用 python serve.py 手动指定端口。")
        sys.exit(1)

    print("=" * 52)
    print("  刷题页已启动")
    print("  让 iPad 连上和这台电脑同一个 WiFi，然后用 Safari 打开：")
    print()
    for ip in lan_ips():
        print(f"      http://{ip}:{PORT}/")
    print()
    print("  打开后点「分享 → 添加到主屏幕」，以后点图标直接进。")
    print("  关闭这个窗口就停止服务。")
    print("=" * 52)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
