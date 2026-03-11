"""Unit tests for SSRF-aware networking primitives."""

from __future__ import annotations

import socket
import unittest

from aiohttp.abc import AbstractResolver, ResolveResult

from websurfer_mcp.networking import SafeResolver, UnsafeAddressError
from websurfer_mcp.url_validation import URLValidator


class StubResolver(AbstractResolver):
    """Simple resolver stub for testing SafeResolver."""

    def __init__(self, results: list[ResolveResult]) -> None:
        self.results = results
        self.closed = False

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> list[ResolveResult]:
        return self.results

    async def close(self) -> None:
        self.closed = True


class TestSafeResolver(unittest.IsolatedAsyncioTestCase):
    """Tests for the DNS safety wrapper."""

    async def test_resolve_allows_public_addresses(self):
        resolver = SafeResolver(
            URLValidator(),
            resolver=StubResolver(
                [
                    ResolveResult(
                        hostname="example.com",
                        host="93.184.216.34",
                        port=443,
                        family=socket.AF_INET,
                        proto=socket.IPPROTO_TCP,
                        flags=socket.AI_NUMERICHOST,
                    )
                ]
            ),
        )

        result = await resolver.resolve("example.com", 443)
        self.assertEqual(result[0]["host"], "93.184.216.34")

    async def test_resolve_rejects_private_addresses(self):
        resolver = SafeResolver(
            URLValidator(),
            resolver=StubResolver(
                [
                    ResolveResult(
                        hostname="example.com",
                        host="127.0.0.1",
                        port=443,
                        family=socket.AF_INET,
                        proto=socket.IPPROTO_TCP,
                        flags=socket.AI_NUMERICHOST,
                    )
                ]
            ),
        )

        with self.assertRaises(UnsafeAddressError) as context:
            await resolver.resolve("example.com", 443)

        self.assertIn("127.0.0.1", str(context.exception))

    async def test_resolve_rejects_mixed_public_and_private_answers(self):
        resolver = SafeResolver(
            URLValidator(),
            resolver=StubResolver(
                [
                    ResolveResult(
                        hostname="example.com",
                        host="93.184.216.34",
                        port=443,
                        family=socket.AF_INET,
                        proto=socket.IPPROTO_TCP,
                        flags=socket.AI_NUMERICHOST,
                    ),
                    ResolveResult(
                        hostname="example.com",
                        host="10.0.0.5",
                        port=443,
                        family=socket.AF_INET,
                        proto=socket.IPPROTO_TCP,
                        flags=socket.AI_NUMERICHOST,
                    ),
                ]
            ),
        )

        with self.assertRaises(UnsafeAddressError) as context:
            await resolver.resolve("example.com", 443)

        self.assertIn("10.0.0.5", str(context.exception))

    async def test_close_closes_wrapped_resolver(self):
        stub = StubResolver([])
        resolver = SafeResolver(URLValidator(), resolver=stub)

        await resolver.close()
        self.assertTrue(stub.closed)


if __name__ == "__main__":
    unittest.main()
