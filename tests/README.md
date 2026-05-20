# Testing and Validation

This project now includes two levels of validation:

1. Unit-level checks (`tests/`) for core correctness:
- password policy schema validation
- text cleaning helpers
- Redis cache key normalization

2. End-to-end workflow validation (`scripts/validate_e2e.py`):
- register admin
- login admin
- create department
- upload document
- register/login user
- ask question
- ask same question again (cache flow exercised)

## Run Unit Tests

```powershell
pip install -r requirements-test.txt
pytest -q
```

## Run End-to-End Validation

Prerequisites:
- Backend running
- Redis running
- A sample PDF/DOCX file available

```powershell
python scripts/validate_e2e.py --base-url http://127.0.0.1:8002 --pdf "C:\path\to\sample.pdf"
```

If all checks pass, it prints `E2E validation passed.` with summary metadata.
