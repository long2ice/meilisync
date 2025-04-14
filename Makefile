checkfiles = meilisync/ tests/ conftest.py
py_warn = PYTHONDEVMODE=1

style:
	@ruff format $(checkfiles)
	@ruff check $(checkfiles) --fix

check:
	@mypy $(checkfiles)

test:
	$(py_warn) pytest --suppress-no-test-exit-code

ci: check test

build:
	@poetry build
