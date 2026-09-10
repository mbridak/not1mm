"""Tests for not1mm.lib.n1mm.N1MM score sending."""

import socket

from not1mm.lib.n1mm import N1MM

SCORE_XML = (
    '<?xml version="1.0"?><dynamicresults><contest>CQ-WPX-CW</contest>'
    "<call>WT2P</call><score>12345</score>"
    '<breakdown><qso band="total" mode="ALL">42</qso>'
    '<point band="total" mode="ALL">120</point></breakdown></dynamicresults>'
)


def _bound_udp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(1.0)
    return sock, sock.getsockname()[1]


def test_send_score_transmits_xml_verbatim():
    sock, port = _bound_udp_socket()
    try:
        n1mm = N1MM(scoreport=f"127.0.0.1:{port}")
        n1mm.send_score(SCORE_XML)
        received = sock.recv(65535)
    finally:
        sock.close()
    assert received.decode() == SCORE_XML


def test_send_score_accepts_bytes():
    sock, port = _bound_udp_socket()
    try:
        n1mm = N1MM(scoreport=f"127.0.0.1:{port}")
        n1mm.send_score(SCORE_XML.encode())
        received = sock.recv(65535)
    finally:
        sock.close()
    assert received.decode() == SCORE_XML


def test_send_score_fans_out_and_skips_malformed_targets():
    sock_a, port_a = _bound_udp_socket()
    sock_b, port_b = _bound_udp_socket()
    try:
        n1mm = N1MM(
            scoreport=f"127.0.0.1:{port_a} not-a-valid-target 127.0.0.1:{port_b}"
        )
        n1mm.send_score(SCORE_XML)
        assert sock_a.recv(65535).decode() == SCORE_XML
        assert sock_b.recv(65535).decode() == SCORE_XML
    finally:
        sock_a.close()
        sock_b.close()
