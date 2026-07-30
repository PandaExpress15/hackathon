.PHONY: install dev run test smoke demo verify package lint

install:
	python -m pip install -r requirements.txt

dev:
	python -m pip install -r requirements-dev.txt

run:
	python app.py

test:
	pytest -q

smoke:
	python scripts/smoke_test_app.py

demo:
	python scripts/run_demo_checks.py

verify:
	python scripts/verify_submission.py

package:
	python scripts/build_submission.py

lint:
	ruff check .
