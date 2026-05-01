import unittest

from neutrino_py.packet import decode_packet, encode_packet, frame, unframe_prefix


class PacketTests(unittest.TestCase):
    def test_packet_round_trip(self):
        raw = encode_packet(7, b"hello", flags=3)
        sequence, flags, payload = decode_packet(raw)
        self.assertEqual(sequence, 7)
        self.assertEqual(flags, 3)
        self.assertEqual(payload, b"hello")

    def test_frame_round_trip(self):
        buffer = bytearray(frame(b"abc"))
        self.assertEqual(unframe_prefix(buffer), b"abc")
        self.assertEqual(buffer, bytearray())


if __name__ == "__main__":
    unittest.main()

