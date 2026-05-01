import asyncio
import unittest

from neutrino_py import Client, Doctor, Server


class CoreTests(unittest.TestCase):
    def test_doctor_system_info(self):
        info = Doctor().system_info()
        self.assertIn("python", info)
        self.assertIn("python_32bit", info)

    def test_client_server_echo(self):
        async def run():
            server = Server(port=0)
            await server.start()
            sockets = server._server.sockets
            port = sockets[0].getsockname()[1]
            client = Client(port=port)
            try:
                response = await client.send(b"hello")
                self.assertEqual(response, b"hello")
            finally:
                await client.close()
                await server.stop()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()

