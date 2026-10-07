#!/usr/bin/env python3
"""Execute 16 independently selected existing behavioral fixtures.
The selection reads test definitions only; no assertion inspects source code.
These are portable fixtures, not real Herdr/Claude/Pi lifecycle acceptance.
"""
from pathlib import Path
import os
import re
import subprocess

root = Path.cwd()
selections = {
    'fm-backend-herdr.test.sh': [
        'test_missing_registration_requires_process_evidence',
        'test_registration_parser_preserves_unknown_and_business_errors',
        'test_strict_missing_registration_process_snapshots',
        'test_original_process_incarnation_stop_proof',
        'test_recovery_grade_read_widens_only_at_its_own_boundary',
        'test_stale_registration_over_a_shell_only_pane_is_agent_free',
        'test_stale_registration_ignores_status_and_reads_the_process',
        'test_busy_state_never_reports_a_shell_only_pane_busy',
    ],
    'fm-control-relaunch.test.sh': [
        'test_herdr_missing_registration_never_relaunches_a_surviving_original',
        'test_herdr_relaunch_requires_real_stop_and_replacement_incarnation',
        'test_herdr_relaunch_rechecks_the_shell_at_the_typing_boundary',
        'test_herdr_stop_postcondition_cannot_borrow_a_false_dead_read',
    ],
    'fm-crew-state.test.sh': [
        'test_no_run_herdr_missing_registration_without_os_proof_refuses',
        'test_no_run_herdr_stale_registration_over_shell_reads_agent_gone',
        'test_no_run_herdr_stale_working_record_is_never_busy',
    ],
    'fm-agy-harness.test.sh': [
        'test_herdr_unregistered_pane_without_process_proof_refuses',
    ],
}
env = os.environ.copy()
env.pop('TMPDIR', None)
env['FM_TEST_BASE_PATH'] = env['PATH']
for filename, selectors in selections.items():
    text = (root / 'tests' / filename).read_text()
    text = text[:re.search(r'^test_[a-z0-9_]+$', text, re.M).start()]
    driver = root / 'tests/.fm-focused-16-validation.sh'
    driver.write_text(text + '\n' + '\n'.join(selectors) + '\n')
    print('Executing existing fixture functions from ' + filename, flush=True)
    try:
        result = subprocess.run(['bash', str(driver)], env=env)
    finally:
        driver.unlink(missing_ok=True)
    if result.returncode:
        raise SystemExit(result.returncode)
