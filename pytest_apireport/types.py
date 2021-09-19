from typing import Literal, Protocol, TypedDict


class TestReporter(Protocol):
    """Methods defined in order of execution."""

    def report_test_run_start(self) -> int:
        pass

    def report_test_start(self, test_name: str) -> int:
        pass

    def report_test_finish(self, test_id: int, test_status: str) -> None:
        pass

    def report_test_run_finish(self, run_id: int) -> None:
        pass


TestReportEvent = Literal["test_start", "test_finish"]
TestRunReportEvent = Literal["test_run_start", "test_run_finish"]


class TestReportStats(TypedDict):
    timestamp: str
    node_id: str
    test_id: int
    event: TestReportEvent


class TestRunReportStats(TypedDict):
    timestamp: str
    run_id: int
    event: TestRunReportEvent
