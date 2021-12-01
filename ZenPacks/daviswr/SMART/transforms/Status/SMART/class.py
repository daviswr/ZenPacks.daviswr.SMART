#pylint: disable=invalid-name
from Products.ZenEvents import Event

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
        HEALTH_FAILED: Event.Error,
        HEALTH_PASSED: Event.Clear,
        HEALTH_UNKNOWN: Event.Warning,
        }
elif 'smart_enabled' in evt.eventKey:
    metric = 'SMART'
    states = {
        SMART_DISABLED: 'is disabled',
        SMART_ENABLED: 'is enabled',
        SMART_UNKNOWN: 'state unknown',
        }
    severity = {
        SMART_DISABLED: Event.Error,
        SMART_ENABLED: Event.Clear,
        SMART_UNKNOWN: Event.Warning,
        }
    # Report component as "down" if SMART is disabled
    evt.eventClass = '/Status'

if 'reallocated' in evt.eventKey:
    # Threshold will set severity to Error
    evt.summary = '{0} sector reallocation has occurred {1} time'.format(
        'Offline' if 'offline' in evt.eventKey else 'Online',
        current
        )
    if current > 1:
        evt.summary += 's'
    evt.dedupid = '{0}|{1}'.format(evt.dedupid, current)
else:
    evt.summary = '{0} {1}'.format(metric, states.get(current, 'unknown'))
    evt.severity = severity.get(current, Event.Warning)
