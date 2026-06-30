"""Unit tests for the dependency-light FileHelper utilities (no spaCy/torch)."""
import pandas as pd

from helper.filehelper import FileHelper


def test_check_file_size(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    nonempty = tmp_path / "data.txt"
    nonempty.write_text("hello")
    assert FileHelper.check_file_size(str(nonempty)) is True
    assert FileHelper.check_file_size(str(empty)) is False
    assert FileHelper.check_file_size(str(tmp_path / "missing.txt")) is False


def test_file_must_transform():
    assert FileHelper.file_must_transform("application/json", "application/json") is False
    assert FileHelper.file_must_transform("application/json", "text/csv") is True


def test_normalize_entry_flattens_one_level():
    flat = FileHelper.normalize_entry({"a": 1, "nested": {"x": 10, "y": 20}})
    assert flat == {"a": 1, "nested_x": 10, "nested_y": 20}


def test_add_to_json_if_exists():
    helper = FileHelper()
    goal = {}
    out = helper.add_to_json_if_exists(goal, {"text": "hi"}, "text", "pre_", "_suf")
    assert out == {"pre_text_suf": "hi"}
    # absent label leaves the goal untouched
    assert helper.add_to_json_if_exists({}, {"other": 1}, "text", "", "") == {}


def test_normalize_json_expands_results_and_entities():
    helper = FileHelper()
    source = [{
        "text": "Berlin is nice",
        "language": "en",
        "entities": [{"name": "Berlin"}],
        "results": [{"entity": "Berlin", "label": "LOC"}],
    }]
    out = helper.normalize_json(source)
    entry = out[0]
    assert entry["text"] == "Berlin is nice"
    assert entry["language"] == "en"
    assert entry["expected_name_1"] == "Berlin"
    assert entry["recognized_entity_1"] == "Berlin"
    assert entry["recognized_label_1"] == "LOC"


def test_generate_csv_dataframe_response_sorts_text_first():
    df = pd.DataFrame([{"score": 0.9, "text": "Berlin", "language": "en"}])
    response = FileHelper.generate_csv_dataframe_response(df, sort=True)
    assert response.media_type == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
