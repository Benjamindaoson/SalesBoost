from core.exceptions import SalesBoostException, create_error_response


def test_error_response_from_salesboost_exception():
    err = SalesBoostException("boom", error_code="BOOM", details={"foo": "bar"})
    resp = create_error_response(error=err)
    assert resp.get("success") is False
    assert resp["error"]["code"] == "BOOM"
    assert resp["error"]["message"] == "boom"
    # details should be included since provided
    assert resp["error"].get("details") == {"foo": "bar"}


def test_error_response_from_unknown_error():
    resp = create_error_response(error=ValueError("bad"))
    assert resp.get("success") is False
    assert resp["error"]["code"] == "UNKNOWN_ERROR"
    assert resp["error"]["message"] == "An unexpected error occurred"
    # details should include original error information in debug mode
    assert "original_error" in resp["error"].get("details", {})
