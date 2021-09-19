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
    """
    )


@pytest.fixture
def expected_tests_ids_and_statuses(
    request,
) -> Dict[str, Tuple[int, Literal["PASSED", "SKIPPED", "FAILED"]]]:
    module_name = request.node.originalname
    return {
        f"{module_name}.py::test_examples[2-2]": (1, "PASSED"),
        f"{module_name}.py::test_examples[3.14-5.55]": (2, "SKIPPED"),
        f"{module_name}.py::test_examples[nan-42]": (3, "FAILED"),
        f"{module_name}.py::test_properties": (4, "FAILED"),
    }


@pytest.fixture
def test_ids(expected_tests_ids_and_statuses) -> List[int]:
    return [test_id for (test_id, _) in expected_tests_ids_and_statuses.values()]


@pytest.fixture
def test_report_start_handler(
    expected_tests_ids_and_statuses,
) -> Callable[[Request], Response]:
    test_ids_by_node_ids = {
        node_id: test_id
        for node_id, (test_id, _) in expected_tests_ids_and_statuses.items()
    }

    def handler(request: Request):
        data = request.get_json()
        assert isinstance(data, dict)
        assert len(data) == 1
        node_id = data.get("name")
        assert node_id, data.get("name")
        report_id = test_ids_by_node_ids.get(node_id)
        assert report_id, node_id
        return Response(json.dumps({"test_id": report_id}))

    return handler


@pytest.fixture
def test_report_finish_handler_factory(
    expected_tests_ids_and_statuses,
) -> Callable[[int], Callable[[Request], Response]]:
    expected_statuses_by_test_ids = {
        test_id: expected_status
        for (test_id, expected_status) in expected_tests_ids_and_statuses.values()
    }

    def get_handler(test_id: int):
        def handler(request: Request, test_id: int):
            expected_status = expected_statuses_by_test_ids.get(test_id)
            assert expected_status, f"Unexpected request: {request}"
            data = request.get_json()
            assert isinstance(data, dict)
            assert len(data) == 1
            assert data.get("status") == expected_status, data.get("status")
            return Response(status=204)

        return partial(handler, test_id=test_id)

    return get_handler
