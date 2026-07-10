import unittest
from uuid import uuid4

from galerazo_bot.instance_lock import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    def test_second_instance_is_rejected_until_first_releases(self) -> None:
        name = f"test-{uuid4()}"
        first = SingleInstance(name)
        second = SingleInstance(name)

        self.assertTrue(first.acquire())
        try:
            self.assertFalse(second.acquire())
        finally:
            first.release()

        self.assertTrue(second.acquire())
        second.release()


if __name__ == "__main__":
    unittest.main()
