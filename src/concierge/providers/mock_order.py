"""Deterministic seeded mock for OrderProvider (FR-029). No Order table
exists in this MVP's persistence layer (spec.md doesn't model Order as a
first-class entity), so this mock fabricates a stable, deterministic payload
per order_id rather than reading from a database."""

import hashlib


class MockOrderProvider:
    def get_order(self, order_id: str) -> dict | None:
        if not order_id:
            return None
        digest = hashlib.sha256(order_id.encode()).hexdigest()
        return {
            "order_id": order_id,
            "status": "COMPLETED",
            "order_reference": digest[:10].upper(),
        }
