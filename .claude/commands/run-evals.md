# Run OrchestratorOne Adversarial Eval Suite

Runs the full adversarial evaluation suite for OrchestratorOne. First simulates
pre-fix failures to verify the suite catches them, then runs post-fix to confirm
all cases pass and the false-confidence deploy gate is met.

```bash
cd Table10_OrchestratorOne && echo "=== PRE-FIX MODE ===" && python tests/adversarial_evals.py --pre-fix && echo "=== POST-FIX MODE ===" && python tests/adversarial_evals.py
```
