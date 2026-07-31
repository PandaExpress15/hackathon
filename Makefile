.PHONY: run test data verify package

run:
	python app.py

test:
	pytest -q

data:
	python scripts/build_official_data.py

verify:
	python scripts/verify_submission.py

package:
	python scripts/build_submission.py
