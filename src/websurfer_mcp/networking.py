"""Networking primitives with SSRF-aware destination checks."""

from __future__ import annotations

import socket

from aiohttp.abc import AbstractResolver, ResolveResult
from aiohttp.resolver import DefaultResolver

from .url_validation import URLValidator


class UnsafeAddressError(RuntimeError):
    """Raised when a URL resolves to a blocked or non-public destination."""


class SafeResolver(AbstractResolver):
    """DNS resolver that rejects private, loopback, and reserved IP results."""

    def __init__(
        self,
        validator: URLValidator,
        resolver: AbstractResolver | None = None,
    ) -> None:
        self.validator = validator
        self.resolver = resolver or DefaultResolver()

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> list[ResolveResult]:
        """Resolve a hostname and ensure every returned address is publicly routable."""

        results = await self.resolver.resolve(host, port, family)
        if not results:
            raise UnsafeAddressError(f"DNS resolution returned no addresses for {host}")

        safe_results: list[ResolveResult] = []
        for result in results:
            validation = self.validator.validate_resolved_ip(host, result["host"])
            if not validation.is_valid:
                raise UnsafeAddressError(
                    validation.error_message
                    or f"Access to resolved address for {host} is not allowed"
                )
            safe_results.append(result)

        return safe_results

    async def close(self) -> None:
        """Close the wrapped resolver."""

        await self.resolver.close()
