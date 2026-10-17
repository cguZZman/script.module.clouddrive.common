import http.client
import http.server
import io
import re
import threading
import unittest

import kodistubs  # noqa: F401
from clouddrive.common.service import upstream
from clouddrive.common.service.download import Download

PAYLOAD = bytes(range(256)) * (5 * 1024 * 1024 // 256 + 7)  # a bit over 5 MB


class Upstream(object):
    """A provider's download server on 127.0.0.1: byte ranges, kept-open connections, and a record of requests."""

    def __init__(self, ignore_ranges=False, redirect_to=None):
        self.requests, self.connections = [], set()
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def do_GET(self):
                owner.connections.add(self.client_address)
                owner.requests.append({'range': self.headers.get('Range'), 'auth': self.headers.get('Authorization'), 'path': self.path})
                if redirect_to and self.path == '/file':
                    self.send_response(302)
                    self.send_header('Location', redirect_to)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                match = re.match(r'bytes=(\d+)-(\d*)', self.headers.get('Range') or '')
                if match and not ignore_ranges:
                    first = int(match.group(1))
                    last = min(int(match.group(2)) if match.group(2) else len(PAYLOAD) - 1, len(PAYLOAD) - 1)
                    body = PAYLOAD[first:last + 1]
                    self.send_response(206)
                    self.send_header('Content-Range', 'bytes %d-%d/%d' % (first, last, len(PAYLOAD)))
                else:
                    body = PAYLOAD
                    self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except OSError:
                    pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = 'http://127.0.0.1:%d/file' % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Player(io.RawIOBase):
    """The player's side: keeps what it receives, and can hang up after some bytes like Kodi probing a file."""

    def __init__(self, hang_up_after=None):
        self.data = bytearray()
        self.hang_up_after = hang_up_after

    def writable(self):
        return True

    def write(self, b):
        if self.hang_up_after is not None and len(self.data) >= self.hang_up_after:
            raise ConnectionAbortedError('player closed the connection')
        self.data.extend(b)
        return len(b)


class Provider(object):
    download_requires_auth = False


class AuthProvider(object):
    download_requires_auth = True

    def prepare_request(self, method, url):
        return type('R', (), {'url': url, 'headers': {'Authorization': 'Bearer t'}})()


def stream(url, range_header=None, player=None, provider=None, command='GET'):
    handler = Download.__new__(Download)  # Only _stream is tested: no HTTP request to the local service itself.
    handler.headers = {'Range': range_header} if range_header else {}
    handler.command = command
    handler.wfile = player or Player()
    handler.sent = {'status': None, 'headers': {}}
    handler.send_response = lambda code, message=None: handler.sent.update(status=code)
    handler.send_header = lambda name, value: handler.sent['headers'].__setitem__(name, value)
    handler.end_headers = lambda: None
    handler._stream(provider or Provider(), url)
    return handler.sent, handler.wfile


class StreamTest(unittest.TestCase):
    def setUp(self):
        upstream.pool.clear()
        self.upstream = Upstream()
        self.addCleanup(self.upstream.close)
        self.addCleanup(upstream.pool.clear)

    def test_open_ended_range_is_read_in_growing_chunks_over_one_connection(self):
        sent, player = stream(self.upstream.url, 'bytes=0-')
        self.assertEqual(sent['status'], 206)
        self.assertEqual(sent['headers']['Content-Range'], 'bytes 0-%d/%d' % (len(PAYLOAD) - 1, len(PAYLOAD)))
        self.assertEqual(sent['headers']['Content-Length'], str(len(PAYLOAD)))
        self.assertEqual(bytes(player.data), PAYLOAD)
        self.assertEqual([r['range'] for r in self.upstream.requests], ['bytes=0-1048575', 'bytes=1048576-3145727', 'bytes=3145728-%d' % (len(PAYLOAD) - 1)])
        self.assertEqual(len(self.upstream.connections), 1)

    def test_probes_that_hang_up_reuse_the_connection(self):
        stream(self.upstream.url, 'bytes=0-', Player(hang_up_after=64 * 1024))
        sent, player = stream(self.upstream.url, 'bytes=4000000-', Player(hang_up_after=64 * 1024))
        stream(self.upstream.url, 'bytes=100-', Player(hang_up_after=64 * 1024))
        self.assertEqual(sent['headers']['Content-Range'], 'bytes 4000000-%d/%d' % (len(PAYLOAD) - 1, len(PAYLOAD)))
        self.assertEqual(bytes(player.data[:10]), PAYLOAD[4000000:4000010])
        self.assertEqual(len(self.upstream.requests), 3)
        self.assertEqual(len(self.upstream.connections), 1, 'one connection for all three probes')

    def test_without_a_range_the_player_gets_the_whole_file(self):
        sent, player = stream(self.upstream.url)
        self.assertEqual(sent['status'], 200)
        self.assertNotIn('Content-Range', sent['headers'])
        self.assertEqual(bytes(player.data), PAYLOAD)

    def test_a_bounded_range_is_one_request(self):
        sent, player = stream(self.upstream.url, 'bytes=10-19')
        self.assertEqual((sent['status'], sent['headers']['Content-Range'], bytes(player.data)), (206, 'bytes 10-19/%d' % len(PAYLOAD), PAYLOAD[10:20]))
        self.assertEqual([r['range'] for r in self.upstream.requests], ['bytes=10-19'])

    def test_a_provider_that_ignores_ranges_is_passed_on(self):
        plain = Upstream(ignore_ranges=True)
        self.addCleanup(plain.close)
        sent, player = stream(plain.url, 'bytes=0-')
        self.assertEqual(sent['status'], 200)
        self.assertEqual(bytes(player.data), PAYLOAD)

    def test_the_authorization_header_only_goes_to_the_same_host(self):
        target = self.upstream.url.replace('127.0.0.1', 'localhost') + '-moved'
        redirecting = Upstream(redirect_to=target)
        self.addCleanup(redirecting.close)
        sent, player = stream(redirecting.url, 'bytes=0-99', provider=AuthProvider())
        self.assertEqual(bytes(player.data), PAYLOAD[:100])
        self.assertEqual(redirecting.requests[0]['auth'], 'Bearer t')
        self.assertIsNone(self.upstream.requests[0]['auth'])

    def test_head_requests_are_passed_on(self):
        sent, player = stream(self.upstream.url, 'bytes=0-', command='HEAD')
        self.assertEqual(sent['status'], 206)
        self.assertEqual(bytes(player.data), b'')


class StaleConnectionTest(unittest.TestCase):
    def test_a_connection_closed_by_the_server_is_replaced(self):
        server = Upstream()
        self.addCleanup(server.close)
        upstream.pool.clear()
        key, connection, response = upstream.fetch(server.url, {'Range': 'bytes=0-9'})
        response.read()
        upstream.pool.release(key, connection, response)
        connection.sock.close()  # Gone, as if the server had closed it while idle.
        connection.sock = None
        stale = upstream.pool._idle[key][0][0]
        original = stale.request

        def fail_once(*args, **kwargs):
            stale.request = original
            raise http.client.RemoteDisconnected('closed while idle')
        stale.request = fail_once
        key, connection, response = upstream.fetch(server.url, {'Range': 'bytes=0-9'})
        self.assertEqual(response.read(), PAYLOAD[:10])
        upstream.pool.clear()


if __name__ == '__main__':
    unittest.main()
