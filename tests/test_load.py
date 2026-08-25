from unittest.mock import MagicMock, patch

from load_to_dwh import load_keys


def test_load_keys_empty_returns_zero():
    assert load_keys([]) == 0


@patch("load_to_dwh.create_engine")
@patch("load_to_dwh.get_s3_client")
def test_load_keys_reads_exactly_given_objects(mock_s3, mock_engine):
    fake_s3 = MagicMock()
    fake_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b'{"symbol":"BTC-USD","price":50000.0,"volume_24h":1.0,"fetched_at":"2024-01-01T10:00:00+00:00"}')}
    mock_s3.return_value = fake_s3
    assert load_keys(["crypto/dt=2024-01-01/1_BTC-USD.json"]) == 1
    assert fake_s3.get_object.call_count == 1
    fake_s3.list_objects_v2.assert_not_called()
