from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from galerazo_bot.database import Database
from galerazo_bot.monetization import (
    CLUB_HISOPO,
    DONATION_TIERS,
    PAID_HISOPOS,
    PaymentPayloadError,
    create_album_context,
    create_payment_payload,
    invoice_spec,
    parse_album_context,
    parse_payment_payload,
)


class MonetizationCatalogTests(unittest.TestCase):
    def test_catalog_is_unique_cosmetic_and_has_varied_prices(self) -> None:
        self.assertEqual(len(PAID_HISOPOS), 13)
        self.assertEqual(len({item.key for item in PAID_HISOPOS}), len(PAID_HISOPOS))
        self.assertEqual(len({item.image_name for item in PAID_HISOPOS}), len(PAID_HISOPOS))
        self.assertEqual(
            [item.price_stars for item in PAID_HISOPOS],
            [35, 50, 75, 100, 150, 200, 250, 300, 350, 500, 650, 1000, 5000],
        )
        self.assertEqual(PAID_HISOPOS[-1].name, "Hisopo Dengue")
        self.assertEqual(CLUB_HISOPO.name, "Hisopo Estelar")
        self.assertEqual(DONATION_TIERS, (25, 100, 500))

    def test_invoice_specs_and_invalid_products(self) -> None:
        donation = invoice_spec("donation", "25")
        self.assertEqual(donation.amount_stars, 25)
        self.assertIsNone(donation.reward_hisopo_key)

        product = invoice_spec("product", "massive")
        self.assertEqual(product.title, "Hisopo Masivo")
        self.assertEqual(product.reward_hisopo_key, "massive")

        club = invoice_spec("subscription", "club")
        self.assertEqual(club.reward_hisopo_key, "stellar")
        self.assertEqual(club.subscription_period.days, 30)

        for kind, item_key in (
            ("donation", "12"),
            ("donation", "２５"),
            ("product", "missing"),
            ("subscription", "missing"),
            ("other", "25"),
        ):
            with self.subTest(kind=kind, item_key=item_key), self.assertRaises(PaymentPayloadError):
                invoice_spec(kind, item_key)

    def test_signed_payment_payload_roundtrip_and_rejections(self) -> None:
        payload = create_payment_payload(
            "token",
            kind="product",
            item_key="massive",
            user_id="123",
            source_chat_id="-1001",
        )
        intent = parse_payment_payload("token", payload, expected_user_id="123")
        self.assertEqual((intent.kind, intent.item_key, intent.source_chat_id), ("product", "massive", "-1001"))

        no_chat = create_payment_payload(
            "token", kind="donation", item_key="25", user_id="123"
        )
        self.assertIsNone(parse_payment_payload("token", no_chat).source_chat_id)

        with self.assertRaisesRegex(PaymentPayloadError, "otra persona"):
            parse_payment_payload("token", payload, expected_user_id="456")
        with self.assertRaisesRegex(PaymentPayloadError, "firma"):
            parse_payment_payload("wrong-token", payload)
        with self.assertRaisesRegex(PaymentPayloadError, "no es válido"):
            parse_payment_payload("token", "short")

        parts = payload.split(":")
        parts[0] = "h0"
        with self.assertRaisesRegex(PaymentPayloadError, "firma"):
            parse_payment_payload("token", ":".join(parts))

        with self.assertRaisesRegex(PaymentPayloadError, "límite"):
            create_payment_payload(
                "token",
                kind="donation",
                item_key="25",
                user_id="123",
                source_chat_id="x" * 200,
            )

    def test_signed_album_context_roundtrip_and_rejections(self) -> None:
        value = create_album_context("token", chat_id="-1001", user_id="123")
        self.assertEqual(parse_album_context("token", value, expected_user_id="123"), "-1001")
        for candidate, user_id in (
            ("bad", "123"),
            (value, "456"),
            (value[:-1] + ("0" if value[-1] != "0" else "1"), "123"),
        ):
            with self.subTest(candidate=candidate, user_id=user_id), self.assertRaises(ValueError):
                parse_album_context("token", candidate, expected_user_id=user_id)


class MonetizationDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temporary.name) / "test.sqlite3")
        self.db.get_or_create_user("1", "Uno", "uno")
        self.db.get_or_create_user("2", "Dos", "dos")
        self.db.register_chat("-2", "supergroup", "Zeta")
        self.db.register_chat("-1", "group", "Alfa")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _payment(
        self,
        charge_id: str,
        *,
        user_id: str = "1",
        kind: str = "donation",
        item_key: str = "25",
        reward: str | None = None,
        amount: int = 25,
        paid_at: str = "2026-08-27T10:00:00+00:00",
        expires: str | None = None,
    ) -> bool:
        return self.db.record_star_payment(
            telegram_payment_charge_id=charge_id,
            provider_payment_charge_id=f"provider-{charge_id}",
            user_id=user_id,
            kind=kind,
            item_key=item_key,
            amount_stars=amount,
            currency="XTR",
            invoice_payload=f"payload-{charge_id}",
            source_chat_id="-1",
            reward_hisopo_key=reward,
            paid_at=paid_at,
            is_recurring=kind == "subscription",
            is_first_recurring=charge_id.endswith("1"),
            subscription_expiration_date=expires,
        )

    def test_albums_ownership_payments_refunds_and_donors(self) -> None:
        with self.db._connect() as conn:
            conn.executemany(
                """
                INSERT INTO hisopo_collections (
                    chat_id, user_id, hisopo_type, capture_count,
                    first_captured_at, last_captured_at
                ) VALUES (?, '1', ?, ?, 'first', 'last')
                """,
                (("-2", "gold", 2), ("-1", "common", 3), ("-1", "gold", 1)),
            )
        albums = self.db.list_hisopo_albums_for_user("1")
        self.assertEqual(
            [(album.chat_id, album.discovered_count, album.capture_count) for album in albums],
            [("-1", 2, 4), ("-2", 1, 2)],
        )
        self.assertEqual(self.db.list_hisopo_albums_for_user("missing"), [])

        self.assertFalse(self.db.owns_paid_hisopo("1", "serene"))
        self.assertTrue(self._payment("product-1", kind="product", item_key="serene", reward="serene", amount=50))
        self.assertFalse(self._payment("product-1", kind="product", item_key="serene", reward="serene", amount=50))
        self.assertTrue(self._payment("product-2", kind="product", item_key="serene", reward="serene", amount=50, paid_at="2026-08-27T11:00:00+00:00"))
        ownership = self.db.get_paid_hisopo_ownership("1")
        self.assertEqual([(entry.hisopo_key, entry.quantity) for entry in ownership], [("serene", 2)])
        self.assertTrue(self.db.owns_paid_hisopo("1", "serene"))
        self.assertTrue(self.db.refund_star_payment("product-2", refunded_at="2026-08-27T12:00:00+00:00"))
        self.assertEqual(self.db.get_paid_hisopo_ownership("1")[0].quantity, 1)
        self.assertTrue(self.db.refund_star_payment("product-1", refunded_at="2026-08-27T13:00:00+00:00"))
        self.assertEqual(self.db.get_paid_hisopo_ownership("1"), [])
        self.assertFalse(self.db.refund_star_payment("product-1", refunded_at="later"))
        self.assertFalse(self.db.refund_star_payment("missing", refunded_at="later"))

        self.assertIsNone(self.db.get_club_membership("1"))
        self.assertTrue(self._payment("club-1", kind="subscription", item_key="club", reward="stellar", amount=100, expires="2026-09-26T10:00:00+00:00"))
        self.assertTrue(self._payment("club-2", kind="subscription", item_key="club", reward="stellar", amount=100, paid_at="2026-09-26T10:00:00+00:00"))
        membership = self.db.get_club_membership("1")
        self.assertEqual((membership.periods_paid, membership.active_until), (2, "2026-09-26T10:00:00+00:00"))
        self.assertEqual(self.db.get_paid_hisopo_ownership("1")[0].quantity, 2)
        self.assertTrue(self.db.refund_star_payment("club-2", refunded_at="2026-09-27T10:00:00+00:00"))
        self.assertEqual(self.db.get_club_membership("1").periods_paid, 1)
        self.assertTrue(self.db.refund_star_payment("club-1", refunded_at="2026-09-27T11:00:00+00:00"))
        membership = self.db.get_club_membership("1")
        self.assertEqual((membership.periods_paid, membership.active_until), (0, None))
        self.assertEqual(self.db.get_paid_hisopo_ownership("1"), [])

        self.assertFalse(self.db.is_donor_display_public("1"))
        self.db.set_donor_display_public("1", True)
        self.db.set_donor_display_public("1", False)
        self.db.set_donor_display_public("1", True)
        self.assertTrue(self.db.is_donor_display_public("1"))
        self.assertTrue(self._payment("donation-1", amount=25))
        self.assertTrue(self._payment("donation-2", user_id="2", item_key="500", amount=500))
        self.assertTrue(self._payment("paid-product", user_id="2", kind="product", item_key="crimson", reward="crimson", amount=75))
        entries = self.db.get_donor_leaderboard(limit=1)
        self.assertEqual([(entry.user_id, entry.amount_stars, entry.display_public) for entry in entries], [("2", 500, False)])
        self.assertTrue(self.db.refund_star_payment("donation-2", refunded_at="2026-08-28T10:00:00+00:00"))
        entries = self.db.get_donor_leaderboard()
        self.assertEqual([(entry.user_id, entry.amount_stars, entry.display_public) for entry in entries], [("1", 25, True)])


if __name__ == "__main__":
    unittest.main()
