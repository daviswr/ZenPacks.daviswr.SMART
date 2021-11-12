#pylint: disable=line-too-long,no-init,invalid-name,too-few-public-methods
""" Parses performance data from smartctl """

import re

from Products.ZenEvents import Event
from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenUtils.Utils import prepId

from ZenPacks.daviswr.SMART.lib.util import (
    HEALTH_FAILED,
    HEALTH_PASSED,
    HEALTH_UNKNOWN,
    SMART_DISABLED,
    SMART_ENABLED,
    SMART_UNKNOWN,
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
                for term in key_raw.strip().replace('-', ' ').split(' '):
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
        hard_disk = isinstance(info.get('RotationRate', ''), int)

        ## Attributes
        attrs = dict()

        # Example:
        # ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE  # noqa
        #   1 Raw_Read_Error_Rate     0x000a   098   098   000    Old_age   Always       -       0  # noqa
        #   5 Reallocated_Sector_Ct   0x0013   100   100   050    Pre-fail  Always       -       0  # noqa
        #  12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       6860  # noqa
        # 194 Temperature_Celsius     0x0023   077   062   030    Pre-fail  Always       -       23 (Min/Max 10/38)  # noqa
        attr_re = r'(\d+) (\S+)\s+0x\w{4}   (\d+)   \d+   (\d+)    (\S+)\s+\w+\s+\S+\s+(\d+)'  # noqa

        matches = re.findall(attr_re, cmd.result.output)
        for match in matches:
            attr_id, name, value, threshold, attr_type, raw = match
            name = name.replace('_', ' ')
            if name.startswith('Unknown') and name.endswith('Attribute'):
                name = attr_override.get(name, '{0} {1}'.format(name, attr_id))
            value = int(value)
            threshold = int(threshold)
            attr_type = attr_type.replace('_', ' ').lower()
            raw = int(raw)  # RegEx should only match the digits
            if value > 100:
                # Kingston SSDs scale some noramlized values to 120
                if value <= 120:
                    scale = 1.2
                # WD drives scale some normalized values to 200
                elif value <= 200:
                    scale = 2.0
                # 0-253 are possible values
                # https://kb.vmware.com/s/article/2040405
                # Observed on some Samsung SSDs
                elif value <= 253:
                    scale = 2.53
                elif value > 253:
                    scale = value/100.0
                value = value/scale
                threshold = value/scale
            attrs[attr_id] = {
                'name': name,
                'value': value,
                'threshold': threshold,
                'type': attr_type,
                'raw': raw,
                }

            # Health threshold events
            if threshold > 0 and value <= threshold:
                result.events.append({
                    'device': cmd.deviceConfig.device,
                    'component': prepId(component),
                    'severity': Event.Error,
                    'eventKey': name.replace(' ', ''),
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
                    'component': prepId(component),
                    'severity': Event.Clear,
                    'eventKey': name.replace(' ', ''),
                    'eventClass': '/HW/Store',
                    'summary': '{0} {1} health above threshold: {2}%'.format(
                        name,
                        attr_type,
                        value,
                        ),
                    })

        ## Device Stats
        stats = dict()
        # Example:
        # Page  Offset Size        Value Flags Description
        # 0x03  0x020  4               0  ---  Number of Reallocated Logical Sectors  # noqa
        # 0x05  0x008  1              30  ---  Current Temperature
        # 0x07  0x008  1              30  ---  Percentage Used Endurance Indicator  # noqa
        stat_re = r'0x\w{2}  0x\w{3}  \d\s+(\d+)  \S{3}  (\w.*)'
        matches = re.findall(stat_re, cmd.result.output)
        for match in matches:
            value, name = match
            stats[name] = int(value)

        ## Phy Events
        phy_events = 0
        # Example:
        # ID      Size     Value  Description
        # 0x0008  2            0  Device-to-host non-data FIS retries
        # 0x0009  2            3  Transition from drive PhyRdy to drive PhyNRdy
        # 0x000a  2            4  Device-to-host register FISes sent due to a COMRESET  # noqa
        phy_re = r'0x\w{4}  \d\s+(\d+)  (\w.*)'
        matches = re.findall(phy_re, cmd.result.output)
        for match in matches:
            value, name = match
            if name != 'Vendor specific':
                phy_events += int(value)

        ## Assemble datapoint values

        values = dict()
        values['smart_enabled'] = info.get('SmartSupport', SMART_UNKNOWN)
        values['health_check'] = info.get(
            'SmartOverallHealthSelfAssessmentTestResult',
            HEALTH_UNKNOWN
            )
        values['phy_events'] = phy_events

        # Raw attribute values

        # Why not Raw_Read_Error_Rate?
        # From https://wiki.unraid.net/Understanding_SMART_Reports -
        # "Only Seagates report the raw value, which yes, does appear to be the
        # number of raw read errors, but should be ignored, completely. All
        # other drives have raw read errors too, but do not report them,
        # leaving this value as zero only."

        # Reallocated Sectors
        if '5' in attrs:
            values['reallocated_sectors'] = attrs['5']['raw']
        elif 'Number of Reallocated Logical Sectors' in stats:
            value = stats['Number of Reallocated Logical Sectors']
            values['reallocated_sectors'] = value

        if 'reallocated_sectors' in values:
            # "raw" is stored as a gauge, "sectors" as derive/counter
            values['reallocated_raw'] = values['reallocated_sectors']

        if '198' in attrs:
            # "raw" is stored as a gauge, just "offline" as derive/counter
            values['reallocated_offline'] = attrs['5']['raw']
            values['reallocated_offline_raw'] = attrs['5']['raw']

        # Pending Sectors
        if '197' in attrs:
            values['pending_sectors'] = attrs['197']['raw']
        elif 'Number of Realloc. Candidate Logical Sectors' in stats:
            value = stats['Number of Realloc. Candidate Logical Sectors']
            values['pending_sectors'] = value

        # Temperature
        if '194' in attrs:
            values['temperature_celsius'] = attrs['194']['raw']
        elif '190' in attrs:
            values['temperature_celsius'] = attrs['190']['raw']
        elif 'Current Temperature' in info:
            values['temperature_celsius'] = info['Current Temperature']
        elif 'Current Temperature' in stats:
            values['temperature_celsius'] = stats['Current Temperature']
        elif hard_disk and '231' in attrs:
            # Some hard drives may use 231 for Temperature
            values['temperature_celsius'] = attrs['231']['raw']

        # Normalized values
        health_attrs = {
            '1': 'read_error_health',   # Raw_Read_Error_Rate normalized
            '5': 'reallocated_health',  # Reallocated_Sector_Ct normalized
            }

        for attr in health_attrs:
            if attr in attrs:
                values[health_attrs[attr]] = attrs[attr]['value']

        lifetime_health_attrs = [
            '9',   # Power_On_Hours
            '12',  # Power_Cycle_Count
            ]

        for attr in lifetime_health_attrs:
            if attr in attrs:
                values['lifetime_health'] = attrs[attr]['value']
                break

        # https://www.hdsentinel.com/ssd_case_health_decrease_wearout.php
        ssd_health_attrs = [
            '169',  # Remaining Life Percentage
            '173',  # SSD Wear Leveling Count / Media Wearout Indicator
            '177',  # Wear Leveling Count
            '202',  # Data Address Mark Errors / Percent Lifetime Remain
            '231',  # SSD Life Left
            ]

        for attr in ssd_health_attrs:
            if attr in attrs and not (hard_disk and '231' == attr):
                values['ssd_health'] = attrs[attr]['value']
                break

        if 'ssd_health' not in values:
            if 'Percentage Used Endurance Indicator' in stats:
                used = stats['Percentage Used Endurance Indicator']
                values['ssd_health'] = 100 - used
            elif 'Percentage Used' in info:
                values['ssd_health'] = 100 - info['Percentage Used']

        lowest = 100
        for attr in attrs:
            if ('Temperature' not in attrs[attr]['name']
                    and not (0 == attrs[attr]['value']
                             and 0 == attrs[attr]['threshold'])
                    and attr not in lifetime_health_attrs
                    and attr not in ssd_health_attrs
                    and attrs[attr]['value'] < lowest):
                lowest = attrs[attr]['value']

        values['overall_health'] = lowest

        for point in cmd.points:
            if point.id in values:
                result.values.append((point, values[point.id]))
