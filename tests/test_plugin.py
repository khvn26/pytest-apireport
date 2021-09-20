from typing import Dict, List, Tuple

import pytest
from werkzeug.wrappers import Response


def test_plugin__insufficient_args(testdir):
    # arrange
    testmodule = testdir.makepyfile(
        """
    def test_ok():
        pass
    """
    )

    # act
    result = testdir.runpytest(testmodule, "--report-enabled")

    # assert
    assert result.ret == 4
    result.stderr.fnmatch_lines(
        [
            "*--report-enabled should be used with --report-base-url and --report-auth-token*"
        ]
    )


def test_plugin__calls_expected__expected_summary(
    httpserver,
    testdir,
    auth_token,
    testmodule,
    reporting_api,
):
    # act
    result = testdir.runpytest(
        testmodule,
        "--report-enabled",
        "--report-base-url",
        httpserver.url_for(""),
        "--report-auth-token",
        auth_token,
    )

    # assert
    httpserver.check()
    assert result.ret == 1
    result.stdout.re_match_lines(
        [
            ".*test_run_started\tRun ID: 11",
            ".*test_start.*Report ID: 1.*test_examples.*",
            ".*test_finish.*Report ID: 1.*test_examples.*",
            ".*test_start.*Report ID: 2.*test_examples.*",
            ".*test_finish.*Report ID: 2.*test_examples.*",
            ".*test_start.*Report ID: 3.*test_examples.*",
            ".*test_finish.*Report ID: 3.*test_examples.*",
            ".*test_start.*Report ID: 4.*test_properties.*",
            ".*test_finish.*Report ID: 4.*test_properties.*",
            ".*test_start.*Report ID: 5.*test_error_at_setup.*",
            ".*test_finish.*Report ID: 5.*test_error_at_setup.*",
            ".*test_start.*Report ID: 6.*test_error_at_teardown.*",
            ".*test_finish.*Report ID: 6.*test_error_at_teardown.*",
            ".*test_run_finished\tRun ID: 11",
        ]
    )


def test_plugin__xdist_enabled__calls_expected__expected_summary(
    httpserver,
    testdir,
    auth_token,
    testmodule,
    reporting_api,
):
    # act
    result = testdir.runpytest(
        testmodule,
        "--report-enabled",
        "--report-base-url",
        httpserver.url_for(""),
        "--report-auth-token",
        auth_token,
        "-n",
        "2",
    )

    # assert
    httpserver.check()
    assert result.ret == 1
    result.stdout.re_match_lines(
        [
            ".*test_run_started\tRun ID: 11",
            ".*test_run_finished\tRun ID: 11",
        ]
    )
    result.stdout.re_match_lines_random(
        [
            ".*test_start.*Report ID: 1.*test_examples.*",
            ".*test_finish.*Report ID: 1.*test_examples.*",
            ".*test_start.*Report ID: 2.*test_examples.*",
            ".*test_finish.*Report ID: 2.*test_examples.*",
            ".*test_start.*Report ID: 3.*test_examples.*",
            ".*test_finish.*Report ID: 3.*test_examples.*",
            ".*test_start.*Report ID: 4.*test_properties.*",
            ".*test_finish.*Report ID: 4.*test_properties.*",
            ".*test_start.*Report ID: 5.*test_error_at_setup.*",
            ".*test_finish.*Report ID: 5.*test_error_at_setup.*",
            ".*test_start.*Report ID: 6.*test_error_at_teardown.*",
            ".*test_finish.*Report ID: 6.*test_error_at_teardown.*",
        ]
    )
