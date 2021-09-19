from datetime import datetime
from typing import TYPE_CHECKING, Dict, Generator, List

import pytest
from _pytest.config.exceptions import UsageError

from pytest_apireport.api import APITestReporter
from pytest_apireport.types import (
    TestReportEvent,
    TestReportStats,
    TestReporter,
    TestRunReportEvent,
    TestRunReportStats,
)

if TYPE_CHECKING:
    from pytest import Session
    from _pytest.config import Config, PytestPluginManager
    from _pytest.config.argparsing import Parser
    from _pytest.nodes import Item, Node
    from _pytest.reports import CollectReport, TestReport
    from _pytest.terminal import TerminalReporter


def pytest_addoption(parser: "Parser", pluginmanager: "PytestPluginManager") -> None:
    group = parser.getgroup("httpreport", "simple test reporter")
    group.addoption(
        "--report-base-url",
        dest="reportbaseurl",
        default="",
        help="reporting API base url",
    )
    group.addoption(
        "--report-auth-token",
        dest="reportauthtoken",
        default="",
        help="reporting API auth token",
    )
    group.addoption(
        "--report-enabled",
        dest="reportenabled",
        action="store_true",
        help="reporting enabled",
    )


def pytest_configure(config: "Config") -> None:
    if not config.option.reportenabled:
        return

    if not (config.option.reportbaseurl and config.option.reportauthtoken):
        raise UsageError(
            "--report-enabled should be used with --report-base-url and --report-auth-token"
        )

    reporter = get_api_reporter(config)

    api_test_report_plugin = TestReportPlugin(config=config, reporter=reporter)
    config.pluginmanager.register(api_test_report_plugin, "api_test_report_plugin")

    # Only report failed collects and test runs from the main node
    if not hasattr(config, "workerinput"):
        api_collect_plugin = TestCollectReportPlugin(reporter)
        config.pluginmanager.register(api_collect_plugin, "api_collect_plugin")
        api_test_run_plugin = TestRunReportPlugin(reporter)
        config.pluginmanager.register(api_test_run_plugin, "api_test_run_plugin")
        config.pluginmanager.register(ReportSummaryPlugin(), "summary_plugin")


def get_api_reporter(config: "Config") -> APITestReporter:
    return APITestReporter(
        base_url=config.option.reportbaseurl,
        auth_token=config.option.reportauthtoken,
    )


class TestReportPlugin:
    def __init__(self, config: "Config", reporter: TestReporter) -> None:
        self.config = config
        self.reporter = reporter
        self.outcomes_by_report_id: Dict[int, str] = {}
        self.report_stats: List[TestReportStats] = []

        # Report failures correctly in case of xdist -x; borrowed from allure
        self._magicaldoublereport = hasattr(
            self.config, "workerinput"
        ) and self.config.getvalue("maxfail")

    def report_stat(self, node_id: str, test_id: int, event: TestReportEvent) -> None:
        self.report_stats.append(
            {
                "timestamp": datetime.now().isoformat(),
                "node_id": node_id,
                "test_id": test_id,
                "event": event,
            }
        )

    def store_stats(self) -> None:
        self.config.test_report_stats = self.report_stats

    @staticmethod
    def _set_report_test_id(item: "Item", report_test_id: int) -> None:
        item.user_properties.append(("report_test_id", report_test_id))

    @staticmethod
    def _get_report_test_id(item: "Item") -> int:
        return next(kv[1] for kv in item.user_properties if kv[0] == "report_test_id")

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: "Item") -> None:
        node_id = item.nodeid
        report_test_id = self.reporter.report_test_start(test_name=node_id)
        self._set_report_test_id(item=item, report_test_id=report_test_id)
        self.report_stat(node_id=node_id, test_id=report_test_id, event="test_start")

    @pytest.mark.hookwrapper
    def pytest_runtest_makereport(self, item: "Item") -> Generator[None, None, None]:
        report: "TestReport" = (yield).get_result()

        report_test_id = self._get_report_test_id(item)
        prev_outcome = self.outcomes_by_report_id.get(report_test_id)
        if prev_outcome and prev_outcome != "passed":
            # Prevent reporting on successfull teardowns for skipped and failed tests
            return

        outcome = self.outcomes_by_report_id[report_test_id] = report.outcome
        if outcome == "passed" and report.when != "teardown":
            # Report test success only when all stages successful
            return

        status = outcome.upper()
        self.reporter.report_test_finish(test_id=report_test_id, test_status=status)
        self.report_stat(
            node_id=item.nodeid, test_id=report_test_id, event="test_finish"
        )

    def pytest_testnodedown(self, node: "Node") -> None:
        report_stats = node.workeroutput["report_stats"]
        self.report_stats += report_stats

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_sessionfinish(self) -> Generator[None, None, None]:
        yield
        if hasattr(self.config, "workerinput"):
            self.config.workeroutput["report_stats"] = self.report_stats
        self.store_stats()


class TestCollectReportPlugin:
    def __init__(self, reporter: TestReporter) -> None:
        self.reporter = reporter

    @pytest.mark.hookwrapper
    def pytest_collectreport(
        self, report: "CollectReport"
    ) -> Generator[None, None, None]:
        yield
        if report.failed:
            # Retrieve report test id and report failure immediately
            reporter = self.reporter
            report_test_id = reporter.report_test_start(test_name=report.nodeid)
            reporter.report_test_finish(
                test_id=report_test_id, test_status=report.outcome.upper()
            )


class TestRunReportPlugin:
    def __init__(self, reporter: "TestReporter") -> None:
        self.reporter = reporter
        self.report_stats: List[TestRunReportStats] = []

    def report_stat(self, run_id: str, event: TestRunReportEvent) -> None:
        self.report_stats.append(
            {
                "timestamp": datetime.now().isoformat(),
                "run_id": run_id,
                "event": event,
            }
        )

    def store_stats(self, config: "Config") -> None:
        config.test_run_report_stats = self.report_stats

    @pytest.mark.hookwrapper
    def pytest_runtestloop(self, session: "Session") -> Generator[None, None, None]:
        reporter = self.reporter
        run_id = reporter.report_test_run_start()
        self.report_stat(run_id=run_id, event="test_run_started")

        yield

        reporter.report_test_run_finish(run_id=run_id)
        self.report_stat(run_id=run_id, event="test_run_finished")
        self.store_stats(config=session.config)


class ReportSummaryPlugin:
    def pytest_terminal_summary(self, terminalreporter: "TerminalReporter") -> None:
        config = terminalreporter.config
        test_run_report_stats = getattr(config, "test_run_report_stats", [])
        test_report_stats = getattr(config, "test_report_stats", [])
        stats = [
            *test_run_report_stats,
            *test_report_stats,
        ]
        # Sort by timestamp
        stats = sorted(stats, key=lambda d: datetime.fromisoformat(d["timestamp"]))
        terminalreporter.write_sep("=", "API report summary")
        terminalreporter.write_line("date\t\t\t\tevent\t\t\tinfo\t\tnodeid")
        terminalreporter.write_sep("-")
        for stat in stats:
            line = "{timestamp}\t{event}"
            if stat.get("run_id"):
                line += "\tRun ID: {run_id}"
            if stat.get("test_id"):
                line += "\t\tReport ID: {test_id}"
            if stat.get("node_id"):
                line += "    {node_id}"
            terminalreporter.write_line(line.format(**stat))
        len_cases = len(set(s.get("test_id") for s in test_report_stats))
        terminalreporter.write_line(
            f"Cases reported: {len_cases}, test reports sent: {len(test_report_stats)}"
        )
