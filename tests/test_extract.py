import json
from unittest.mock import MagicMock, patch

from extract import run


@patch("extract.get_s3_client")
@patch("extract.fetch_ticker")
def test_extract_writes_to_s3(mock_fetch, mock_s3):
    mock_fetch.return_value = {"price": "50000.0", "volume": "123.4"}
    fake_s3 = MagicMock()
    mock_s3.return_value = fake_s3
    keys = run()
    assert len(keys) == 2
    assert fake_s3.put_object.call_count == 2
    body = json.loads(fake_s3.put_object.call_args.kwargs["Body"])
    assert body["symbol"] == "ETH-USD"
    assert body["price"] == 50000.0
