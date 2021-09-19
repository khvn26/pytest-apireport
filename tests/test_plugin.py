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


@pytest.mark.parametrize("xdist_enabled", [False, True])
@pytest.mark.parametrize("interrupt_after_failure", [False, True])
def test_plugin__calls_expected(
    httpserver,
    testdir,
    auth_token,
    testmodule,
    expected_headers,
    test_report_start_handler,
    test_report_finish_handler_factory,
    test_ids,
    xdist_enabled,
    interrupt_after_failure,
):
    # arrange
    httpserver.expect_oneshot_request(
        "/runs/", headers=expected_headers, method="POST"
    ).respond_with_json({"run_id": 11})

    httpserver.expect_request(
        "/tests/", headers=expected_headers, method="POST"
    ).respond_with_handler(test_report_start_handler)

    for test_id in test_ids:
        httpserver.expect_oneshot_request(
            f"/tests/{test_id}/finish/", headers=expected_headers, method="POST"
        ).respond_with_handler(test_report_finish_handler_factory(test_id=test_id))

    httpserver.expect_oneshot_request(
        "/runs/11/finish/", headers=expected_headers, method="POST"
    ).respond_with_response(Response(status=204))

    args = [
        testmodule,
        "--report-enabled",
        "--report-base-url",
        httpserver.url_for(""),
        "--report-auth-token",
        auth_token,
    ]
    if xdist_enabled:
        args += ["-n", "2"]
    if interrupt_after_failure:
        args += ["-x"]
    expected_ret = 2 if xdist_enabled and interrupt_after_failure else 1

    # act
    result = testdir.runpytest(*args)

    # assert
    assert result.ret == expected_ret
    httpserver.check()


@pytest.mark.parametrize("xdist_enabled", [False, True])
def test_report_summary__expected_output(
    httpserver,
    testdir,
    auth_token,
    testmodule,
    test_report_start_handler,
    test_report_finish_handler_factory,
    test_ids,
    xdist_enabled,
):
    # arrange
    httpserver.expect_oneshot_request("/runs/", method="POST").respond_with_json(
        {"run_id": 11}
    )

    httpserver.expect_request("/tests/", method="POST").respond_with_handler(
        test_report_start_handler
    )

    for test_id in test_ids:
        httpserver.expect_oneshot_request(
            f"/tests/{test_id}/finish/", method="POST"
        ).respond_with_handler(test_report_finish_handler_factory(test_id=test_id))

    httpserver.expect_oneshot_request(
        "/runs/11/finish/", method="POST"
    ).respond_with_response(Response(status=204))

    args = [
        testmodule,
        "--report-enabled",
        "--report-base-url",
        httpserver.url_for(""),
        "--report-auth-token",
        auth_token,
    ]
    if xdist_enabled:
        args += ["-n", "2"]

    # act
    result = testdir.runpytest(*args)

    # assert
    assert result.ret == 1
    result.stdout.re_match_lines_random(
        [
            ".*test_run_started\tRun ID: 11",
            ".*test_start.*Report ID.* 1.*test_examples.*",
            ".*test_finish.*Report ID.* 1.*test_examples.*",
            ".*test_start.*Report ID.* 2.*test_examples.*",
            ".*test_finish.*Report ID.* 2.*test_examples.*",
            ".*test_start.*Report ID.* 3.*test_examples.*",
            ".*test_finish.*Report ID.* 3.*test_examples.*",
            ".*test_run_finished\tRun ID: 11",
            "Cases reported: 4, test reports sent: 8",
        ],
    )
