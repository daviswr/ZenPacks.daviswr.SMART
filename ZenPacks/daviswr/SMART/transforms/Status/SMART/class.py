#pylint: disable=invalid-name
from Products.ZenEvents.ZenEventClasses import Clear, Warning, Error

from ZenPacks.daviswr.SMART.lib.util import (
    HEALTH_FAILED,
    HEALTH_PASSED,
    HEALTH_UNKNOWN,
    SMART_DISABLED,
    SMART_ENABLED,
    SMART_UNKNOWN,
    )

current = int(float(evt.current))
metric = 'SMART status'
states = dict()
severity = dict()

if 'health_check' in evt.eventKey:
    metric = 'Health check'
    states = {
        HEALTH_FAILED: 'failed',
        HEALTH_PASSED: 'passed',
        HEALTH_UNKNOWN: 'result unknown',
        }
    severity = {
        HEALTH_FAILED: Error,
        HEALTH_PASSED: Clear,
        HEALTH_UNKNOWN: Warning,
        }
elif 'smart_enabled' in evt.eventKey:
    metric = 'SMART'
    states = {
        SMART_DISABLED: 'is disabled',
        SMART_ENABLED: 'is enabled',
        SMART_UNKNOWN: 'state unknown',
        }
    severity = {
        SMART_DISABLED: Error,
        SMART_ENABLED: Clear,
        SMART_UNKNOWN: Warning,
        }
    # Report component as "down" if SMART is disabled
    evt.eventClass = '/Status'

evt.summary = '{0} {1}'.format(metric, states.get(current, 'unknown'))
evt.severity = severity.get(current, Warning)
