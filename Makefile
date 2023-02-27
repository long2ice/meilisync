checkfiles = meilisync/ tests/ conftest.py
py_warn = PYTHONDEVMODE=1

style:
	@isort -src $(checkfiles)
	@black $(checkfiles)

check:
	@black --check $(checkfiles)
	@ruff $(checkfiles) --fix
	@mypy $(checkfiles)

test:
	$(py_warn) pytest --suppress-no-test-exit-code

ci: check test
