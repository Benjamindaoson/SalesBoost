from core.error_codes import ERROR_CODE
from core.exceptions import SalesBoostException, create_error_response


def test_error_codes_enum_usage_in_response():
    err = SalesBoostException("invalid input", error_code=ERROR_CODE.INVALID_INPUT)
    resp = create_error_response(error=err)
    assert resp["error"]["code"] == ERROR_CODE.INVALID_INPUT.value
