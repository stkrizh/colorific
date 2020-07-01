SUCCESS=@echo "-----------------------\nSUCCESS\n"


DEFAULT: run


.check-venv:
	@echo "-----------------------"
	@echo "--- Checking virtual environment is activated"
	@{ \
		if [ -z ${CI} ]; then \
			which python | grep "\.venv"; \
		fi; \
	}
	$(SUCCESS)


req-main: .check-venv
	@echo "-----------------------"
	@echo "--- Compiling main requirements to requirements/main.txt"
	pip-compile requirements/main.in > requirements/main.txt
	$(SUCCESS)


req-dev: .check-venv
	@echo "-----------------------"
	@echo "--- Compiling development requirements to requirements/dev.txt"
	pip-compile requirements/dev.in > requirements/dev.txt
	$(SUCCESS)


requirements: req-main req-dev


sync: .check-venv
	@echo "-----------------------"
	@echo "--- Installing dependencies"
	pip-sync requirements/main.txt
	$(SUCCESS)


sync-all: .check-venv
	@echo "-----------------------"
	@echo "--- Installing dependencies"
	pip-sync requirements/main.txt requirements/dev.txt
	$(SUCCESS)


run: .check-venv
	@echo "-----------------------"
	@echo "--- Starting up"
	python -m colorific


format: .check-venv
	@echo "-----------------------"
	@echo "--- Reformatting with black, isort"
	isort --recursive colorific tests
	black colorific tests
	$(SUCCESS)


.black-check: .check-venv
	@echo "-----------------------"
	@echo "--- Running black checks"
	black --check colorific tests
	$(SUCCESS)


.isort-check: .check-venv
	@echo "-----------------------"
	@echo "--- Running black checks"
	isort --check-only --recursive colorific tests
	$(SUCCESS)


.flake: .check-venv
	@echo "-----------------------"
	@echo "--- Running flake8 checks"
	flake8 colorific tests
	$(SUCCESS)


.mypy: .check-venv
	@echo "-----------------------"
	@echo "--- Running mypy checks"
	mypy colorific tests
	$(SUCCESS)


lint: .isort-check .black-check .mypy .flake


test: .check-venv
	@echo "-----------------------"
	@echo "--- Running tests"
	pytest
	$(SUCCESS)
