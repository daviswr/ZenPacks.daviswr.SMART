#pylint: disable=line-too-long,no-init,invalid-name,too-few-public-methods
""" Parses performance data from smartctl """

import re

from Products.ZenEvents import Event
from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenUtils.Utils import prepId

from ZenPacks.daviswr.SMART.lib.util import (
    HEALTH_FAILED,
    HEALTH_PASSED,
    SMART_DISABLED,
    SMART_ENABLED,
    attr_override,
    )


class smartctl(CommandParser):
    """ Parses performance data from smartctl """

    def processResults(self, cmd, result):
        """ Returns metrics from command output """

        ## Colon-delimited values (Info, Health, SCT, etc)
        info = dict()
        for line in cmd.result.output.splitlines():
            if ': ' in line and 'capability' not in line:
                key_raw, value_raw = line.replace(' is', '').split(':', 1)
                key = ''
                for term in key_raw.strip().replace('-', '').split(' '):
                    key += term.title()
                value = value_raw.strip()
                if 'bytes' in value or value[0].isdigit():
                    try:
                        value = int(value.split(' ')[0].replace(',', ''))
                    except ValueError:
                        continue
                elif 'SMART support' == key_raw:
                    value = (SMART_ENABLED if 'Enabled' in value
                             else SMART_DISABLED)
                elif key_raw.startswith('SMART overall-health'):
                    value = (HEALTH_PASSED if 'PASSED' in value
                             else HEALTH_FAILED)
                info[key] = value

        component = info.get('Component', '')

        ## Attributes
        attrs = dict()

        # Example:
        # ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE  # noqa
        #   1 Raw_Read_Error_Rate     0x000a   098   098   000    Old_age   Always       -       0  # noqa
        #   5 Reallocated_Sector_Ct   0x0013   100   100   050    Pre-fail  Always       -       0  # noqa
        #  12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       6860  # noqa
        # 194 Temperature_Celsius     0x0023   077   062   030    Pre-fail  Always       -       23 (Min/Max 10/38)  # noqa
        attr_re = r'(\d+) (\S+)\s+\w+\s+(\d+)\s+\d+\s+(\d+)\s+(\S+)\s+\w+\s+\S+\s+(\d+)'  # noqa

        matches = re.findall(attr_re, cmd.result.output)
        for match in matches:
            attr_id, name, value, threshold, attr_type, raw = match
            # Bad RegEx match in SCT output
            if name[0].isdigit():
                continue
            name = name.replace('_', ' ')
            if name.startswith('Unknown') and name.endswith('Attribute'):
                name = attr_override.get(name, name)
            value = int(value)
            threshold = int(threshold)
            attr_type = attr_type.replace('_', ' ').lower()
            raw = int(raw)  # RegEx should only match the digits
            attrs[attr_id] = {
                'name': name,
                'value': value,
                'threshold': threshold,
                'type': attr_type,
                'raw': raw,
                }

            # Health threshold events
            if value <= threshold:
                result.events.append({
                    'device': cmd.deviceConfig.device,
                    'component': component,
                    'severity': Event.Error,
                    'eventKey': name,
                    'eventClass': '/HW/Store',
                    'summary': '{0} {1} health below threshold: {2}%'.format(
                        name,
                        attr_type,
                        value,
                        ),
                    })
            else:
                result.events.append({
                    'device': cmd.deviceConfig.device,
                    'component': component,
                    'severity': Event.Clear,
                    'eventKey': name,
                    'eventClass': '/HW/Store',
                    'summary': '{0} {1} health above threshold: {2}%'.format(
                        name,
                        attr_type,
                        value,
                        ),
                    })

        ## Device Stats
        stats = dict()
        stat_re = r'[\r\n]\S+\s+\S+\s+\d\s+(\d+)\s+\S{3}\s+(\w.*)'
        matches = re.findall(stat_re, cmd.result.output)
        for match in matches:
            value, name = match
            if not name[0].isdigit():
                stats[name] = int(value)

        ## Phy Events
        phy_events = 0
        phy_re = r'[\r\n]\S+\s+\d\s+(\d+)\s+(\w.*)'
        matches = re.findall(phy_re, cmd.result.output)
        for match in matches:
            value, name = match
            if name != 'Vendor specific' and not name[0].isdigit():
                phy_events += int(value)

        ## Assemble datapoint values

        # Most attributes will be the normalized "health" values, except these
        raw_attrs = [
            '5',    # Reallocated_Sector_Ct
            '194',  # Temperature_Celsius
            '197',  # Current_Pending_Sector
            ]
        # Why not Raw_Read_Error_Rate?
        # From https://wiki.unraid.net/Understanding_SMART_Reports -
        # "Only Seagates report the raw value, which yes, does appear to be the
        # number of raw read errors, but should be ignored, completely. All
        # other drives have raw read errors too, but do not report them,
        # leaving this value as zero only."

        # https://www.hdsentinel.com/ssd_case_health_decrease_wearout.php
        ssd_health_attrs = [
            '169',  # Remaining Life Percentage
            '173',  # SSD Wear Leveling Count / Media Wearout Indicator
            '177',  # Wear Leveling Count
            '202',  # Data Address Mark Errors / Percent Of Rated Lifetime Used
            '231',  # SSD Life Left
            ]

        values = dict()

        for point in cmd.points:
            if point.id in values:
                result.values.append((point, values[point.id]))
