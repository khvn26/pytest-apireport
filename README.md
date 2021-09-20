# pytest-apireport
![](coverage.svg)
## Installation
Clone this repository, create a venv, install with
```bash
$ pip install -e .[test]
```

## Testing
```bash
$ pytest tests/
```

## Configuration
The following arguments are added to pytest:
* `--report-enabled`: Toggle reporting.
* `--report-base-url`: API base url, e.g. `https://api.test.com`.
* `--report-auth-token`: API base url, e.g. `ABCDEF`. Used to authorize requests.

`--report-enabled` requires  `--report-base-url` and `--report-auth-token` to be set.

## Room for improvement
What could be done with more time:
* Backoff and degradation for API client
* Better API request error reporting
* API client generation from OpenAPI schema
* Stress/load testing
* CI pipeline with coverage
* More configuration options (pytest.ini, environment variables)
