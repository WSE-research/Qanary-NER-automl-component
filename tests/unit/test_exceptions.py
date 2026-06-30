"""The custom exceptions carry default and custom messages."""
from helper.my_exceptions import (
    FailedDocBinException,
    FailedTrainingException,
    NoTrainingdataException,
)


def test_default_messages():
    assert "missing" in NoTrainingdataException().message
    assert "training" in FailedTrainingException().message.lower()
    assert "docbins" in FailedDocBinException().message.lower()


def test_custom_message():
    assert NoTrainingdataException("custom").message == "custom"
