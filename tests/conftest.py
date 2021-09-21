import json
from functools import partial
from pathlib import Path
from typing import Callable, Dict, List, Literal, Tuple

import pytest
from werkzeug.wrappers import Request, Response

pytest_plugins = ["pytester"]


@pytest.fixture
def auth_token() -> str:
    return "ABCDEF"


@pytest.fixture
def expected_headers(auth_token) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def testmodule(testdir) -> Path:
    return testdir.makepyfile(
        """
    import pytest
    from hypothesis import strategies as st, given


    @pytest.mark.parametrize(
        "left, right",
        (
            (2, 2),
            pytest.param(3.14, 5.55, marks=pytest.mark.skip("Skipped!")),
            (float("nan"), 42),
        ),
    )
    def test_examples(left, right):
        assert left + right == right + left


    NUMBER = st.integers() | st.floats()


    @given(left=NUMBER, right=NUMBER)
    def test_properties(left, right):
        assert left + right == right + left


    @pytest.fixture
    def error_at_setup():
        raise RuntimeError

    def test_error_at_setup(error_at_setup):
        pass

    @pytest.fixture
    def error_at_teardown():
        yield
        raise RuntimeError

    def test_error_at_teardown(error_at_teardown):
        pass
    """
    )


@pytest.fixture
def expected_tests_ids_and_statuses(
    request,
) -> Dict[str, Tuple[int, Literal["PASSED", "SKIPPED", "FAILED", "ERROR"]]]:
    module_name = request.node.originalname
    return {
        f"{module_name}.py::test_examples[2-2]": (1, "PASSED"),
        f"{module_name}.py::test_examples[3.14-5.55]": (2, "SKIPPED"),
        f"{module_name}.py::test_examples[nan-42]": (3, "FAILED"),
        f"{module_name}.py::test_properties": (4, "FAILED"),
        f"{module_name}.py::test_error_at_setup": (5, "ERROR"),
        f"{module_name}.py::test_error_at_teardown": (6, "ERROR"),
    }


@pytest.fixture
def reporting_api(
    httpserver,
    expected_headers,
    expected_tests_ids_and_statuses,
):
    httpserver.expect_oneshot_request(
        "/runs/", headers=expected_headers, method="POST"
    ).respond_with_json({"run_id": 11})

    for nodeid, (test_id, test_status) in expected_tests_ids_and_statuses.items():
        httpserver.expect_oneshot_request(
            "/tests/", headers=expected_headers, method="POST", json={"name": nodeid}
        ).respond_with_json({"test_id": test_id})
        httpserver.expect_oneshot_request(
            f"/tests/{test_id}/finish/",
            headers=expected_headers,
            method="POST",
            json={"status": test_status},
        ).respond_with_response(Response(status=204))

    httpserver.expect_oneshot_request(
        "/runs/11/finish/", headers=expected_headers, method="POST"
    ).respond_with_response(Response(status=204))
