"""End-to-end smoke for the helper layer: a JSON->CSV transform round-trips
through FileHelper without the heavy ML runtime."""
import pytest

pytestmark = pytest.mark.e2e


def test_json_to_csv_transform_roundtrip():
    from helper.filehelper import FileHelper

    helper = FileHelper()
    generated = [{
        "text": "Angela Merkel was born in Hamburg",
        "language": "en",
        "results": [{"entity": "Hamburg", "label": "LOC"}],
    }]
    # accept-type differs from the source type -> must transform to CSV response
    response = helper.save_generated_json(generated, accept_header="text/csv")
    assert response.media_type == "text/csv"
