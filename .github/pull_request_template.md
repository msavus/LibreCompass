## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Checklist

- [ ] `make check test` passes
- [ ] Tested in a real LibreOffice (please say which version and module) —
      the suite cannot cover menu registration, dialogs, `AsyncCallback` or
      reading files through LibreOffice
- [ ] UNO access stayed inside `office/`
- [ ] HTTP calls run in a worker thread; document and control access goes
      through `main_thread.run_on_main()`
- [ ] New user-visible strings have an English msgid and a German entry in
      `i18n.py`
- [ ] `CHANGELOG.md` updated if the change is user-visible
