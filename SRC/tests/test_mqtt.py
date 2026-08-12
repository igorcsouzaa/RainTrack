import unittest

from mqtt_to_mysql import normalize_uuid, store_payload, validate_data


class FakeCursor:
    def __init__(self):
        self.inserted = []
        self.last_query = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.last_query = query
        if query.startswith("INSERT"):
            self.inserted.append(params)

    def fetchone(self):
        if "SELECT p.id" in self.last_query:
            return {"id": 7}
        return None


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class MqttTests(unittest.TestCase):
    def test_normalizes_mac(self):
        self.assertEqual(normalize_uuid("aa:bb:cc:dd:ee:ff"), "AABBCCDDEEFF")

    def test_validates_sensor_ranges(self):
        self.assertEqual(validate_data("TEMPERATURA", "25.5"), 25.5)
        self.assertIsNone(validate_data("UMIDADE", 101))
        self.assertIsNone(validate_data("TEMPERATURA", "texto"))

    def test_stores_valid_payload_in_one_transaction(self):
        connection = FakeConnection()
        count = store_payload(
            {"uuid": "AA:BB:CC:DD:EE:FF", "TEMPERATURA": 22.5, "UMIDADE": 70},
            connection_factory=lambda: connection,
        )
        self.assertEqual(count, 2)
        self.assertEqual(len(connection.cursor_instance.inserted), 2)
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)

    def test_rejects_invalid_uuid_before_database_connection(self):
        with self.assertRaises(ValueError):
            store_payload({"uuid": "invalid", "TEMPERATURA": 20}, connection_factory=lambda: self.fail())


if __name__ == "__main__":
    unittest.main()
