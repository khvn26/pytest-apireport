from typing import Literal, Optional, Type, TypeVar

import requests
from pydantic import BaseModel


class Dto(BaseModel):
    pass


T = TypeVar("T", bound=Dto)


def map_from_json(json_data: dict, cls: Type[T]) -> T:
    return cls(**json_data)


def map_to_json(dto: Dto) -> str:
    return dto.json()


def api_request(
    method: str,
    url: str,
    auth_token: str,
    request: Optional[Dto] = None,
    response_cls: Optional[Type[T]] = None,
) -> Optional[T]:
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    json_str: Optional[str] = None
    if request:
        json_str = map_to_json(request)
    resp = requests.request(method=method, url=url, data=json_str, headers=headers)
    resp.raise_for_status()
    if response_cls:
        return map_from_json(json_data=resp.json(), cls=response_cls)
    return None


class RunsResponse(Dto):
    run_id: int


class TestsRequest(Dto):
    name: str


class TestsResponse(Dto):
    test_id: int


class TestsFinishRequest(Dto):
    status: Literal["PASSED", "FAILED", "SKIPPED", "ERROR"]


class APITestReporter:
    """Methods defined in order of execution."""

    def __init__(self, base_url: str, auth_token: str) -> None:
        self.base_url = base_url
        self.auth_token = auth_token

    def report_test_run_start(self) -> int:
        url = f"{self.base_url}/runs/"
        response: RunsResponse = api_request(
            method="POST",
            auth_token=self.auth_token,
            url=url,
            response_cls=RunsResponse,
        )
        return response.run_id

    def report_test_start(self, test_name: str) -> int:
        url = f"{self.base_url}/tests/"
        request = TestsRequest(name=test_name)
        response: TestsResponse = api_request(
            method="POST",
            auth_token=self.auth_token,
            url=url,
            request=request,
            response_cls=TestsResponse,
        )
        return response.test_id

    def report_test_finish(self, test_id: int, test_status: str) -> None:
        url = f"{self.base_url}/tests/{test_id}/finish/"
        request = TestsFinishRequest(status=test_status)
        api_request(
            method="POST",
            auth_token=self.auth_token,
            url=url,
            request=request,
        )

    def report_test_run_finish(self, run_id: int) -> None:
        url = f"{self.base_url}/runs/{run_id}/finish/"
        api_request(
            method="POST",
            auth_token=self.auth_token,
            url=url,
        )
