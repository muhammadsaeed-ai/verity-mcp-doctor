## Summary
What does this change improve?

## Safety / protocol impact
- [ ] No active tool calls added to the default probe
- [ ] Subprocess execution remains shell-free and time-bounded
- [ ] Output is bounded and sensitive data is not copied into findings
- [ ] Protocol version support and any behavior changes are documented

## Validation
- [ ] Tests added or updated
- [ ] `python -m pytest`
- [ ] `ruff check src tests`
- [ ] README/docs updated where behavior changed
