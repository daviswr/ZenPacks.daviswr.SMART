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
    gen_comp_id,
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
                value = value_raw.strip().replace('%', '')
                if 'bytes' in value or value[0].isdigit():
                    try:
                        value = int(value.split(' ')[0].replace(',', ''))
                    except ValueError:
                        if 'Min/Max' not in key_raw:
                            continue
                elif 'SMART support' == key_raw:
                    value = (SMART_ENABLED if 'Enabled' in value
                             else SMART_DISABLED)
                elif key_raw.startswith('SMART overall-health'):
                    value = (HEALTH_PASSED if 'PASSED' in value
                             else HEALTH_FAILED)
                elif 'SMART Health Status' == key_raw:
                    value = (HEALTH_PASSED if 'OK' in value
                             else HEALTH_FAILED)
                info[key] = value

        component = info.get('Component', '')
        hard_disk = (isinstance(info.get('RotationRate', ''), int)
                     or 'disk' == info.get('DeviceType', ''))

        # Temperature Threshold
        # SCSI
        if ('CurrentDriveTemperature' in info
                and 'DriveTripTemperature' in info):
            temp_event = True
            event_key = 'CurrentDriveTemperature'
            current = info[event_key]
            critical = info.get('DriveTripTemperature', 255)
            warning = 255
        # NVMe
        elif 'Temperature' in info:
            temp_event = True
            event_key = 'Temperature'
            current = info[event_key]
            critical = info.get('CriticalComp.Temp.Threshold', 255)
            warning = info.get('WarningComp.Temp.Threshold', 255)
        # (S)ATA
        elif 'CurrentTemperature' in info:
            temp_event = True
            event_key = 'CurrentTemperature'
            current = info[event_key]
            crit_str = info.get('Min/MaxTemperatureLimit', '0/255 Fake')
            warn_str = info.get('Min/MaxRecommendedTemperature', '0/255 Fake')
            temp_re = r'\d+/(\d+)'
            match = re.search(temp_re, crit_str)
            critical = match.groups()[0] if match else 255
            match = re.search(temp_re, warn_str)
            warning = match.groups()[0] if match else 255
        else:
            temp_event = False

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
                attr_severity = Event.Error
                attr_status = 'below'
            else:
                attr_severity = Event.Clear
                attr_status = 'above'
            result.events.append({
                'device': cmd.deviceConfig.device,
                'component': prepId(gen_comp_id(component)),
                'severity': attr_severity,
                'eventKey': name.replace(' ', ''),
                'eventClass': '/HW/Store',
                'summary': '{0} {1} health {2} threshold: {3}%'.format(
                    name,
                    attr_type,
                    attr_status,
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

        # Temperature threshold if not available in the info dict
        if 'Current Temperature' in stats and not temp_event:
            temp_event = True
            current = stats['Current Temperature']
            event_key = 'CurrentTemperature'
            critical = stats.get(
                'Specified Maximum Operating Temperature',
                255
                )
            warning = 255

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

        ## Generate Threshold Events

        # NVMe available spare capacity
        if 'AvailableSpare' in info:
            nvme_current = info['AvailableSpare']
            if nvme_current <= info.get('AvailableSpareThreshold', -1):
                severity = Event.Error
                status = 'below'
            else:
                severity = Event.Clear
                status = 'above'
            result.events.append({
                'device': cmd.deviceConfig.device,
                'component': prepId(gen_comp_id(component)),
                'severity': severity,
                'eventKey': 'NvmeAvailableSpare',
                'eventClass': '/HW/Store',
                'summary': 'NVMe available spare {0} threshold: {1}%'.format(
                    status,
                    nvme_current
                    ),
                })

        # Temperature
        if temp_event:
            if current >= critical:
                severity = Event.Error
                status = 'above'
            elif current >= warning:
                severity = Event.Warning
                status = 'above'
            else:
                severity = Event.Clear
                status = 'below'
            result.events.append({
                'device': cmd.deviceConfig.device,
                'component': prepId(gen_comp_id(component)),
                'severity': severity,
                'eventKey': event_key,
                'eventClass': '/HW/Store',
                'summary': 'Temperature {0} threshold: {1} degrees'.format(
                    status,
                    current
                    ),
                })

        ## Assemble datapoint values

        values = dict()
        values['smart_enabled'] = info.get(
            'SmartSupport',
            (SMART_ENABLED
             if 'Device supports SMART and is Enabled' in cmd.result.output
             or 'SMART/Health Information' in cmd.result.output
             else SMART_UNKNOWN)
            )
        values['health_check'] = info.get(
            'SmartOverallHealthSelfAssessmentTestResult',
            info.get('SmartHealthStatus', HEALTH_UNKNOWN)
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
        elif 'ElementsInGrownDefectList' in info:
            value = info['ElementsInGrownDefectList']
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
        elif hard_disk and '231' in attrs:
            # Some hard drives may use 231 for Temperature
            values['temperature_celsius'] = attrs['231']['raw']
        elif 'Temperature' in attrs.get('189', {}).get('name', ''):
            values['temperature_celsius'] = attrs['189']['raw']
        elif temp_event:
            values['temperature_celsius'] = current

        # Normalized values
        health_attrs = {
            '1': 'read_error_health',   # Raw Read Error Rate normalized
            '5': 'reallocated_health',  # Reallocated Sector Ct normalized
            }

        for attr in health_attrs:
            if attr in attrs:
                values[health_attrs[attr]] = attrs[attr]['value']

        lifetime_health_attrs = [
            '9',    # Power On Hours
            '193',  # Load Cycle Count
            '225',  # Load/Unload Cycle Count
            '12',   # Power Cycle Count
            ]

        for attr in lifetime_health_attrs:
            if attr in attrs:
                values['lifetime_health'] = attrs[attr]['value']
                break

        if 'lifetime_health' not in values:
            # Load/Unload Cycle Count
            if ('SpecifiedLoadUnloadCountOverDeviceLifetime' in info
                    and 'AccumulatedLoadUnloadCycles' in info):
                total = info['SpecifiedLoadUnloadCountOverDeviceLifetime']  # noqa
                used = info['AccumulatedLoadUnloadCycles']
                values['lifetime_health'] = used / float(total)
            # Power Cycle Count
            elif ('SpecifiedCycleCountOverDeviceLifetime' in info
                    and 'AccumulatedStartStopCycles' in info):
                total = info['SpecifiedCycleCountOverDeviceLifetime']
                used = info['AccumulatedStartStopCycles']
                values['lifetime_health'] = used / float(total)

        # https://www.hdsentinel.com/ssd_case_health_decrease_wearout.php
        ssd_health_attrs = [
            '169',  # Remaining Life Percentage
            '202',  # Percent Lifetime Remain / Data Address Mark Errors
            '173',  # SSD Wear Leveling Count / Media Wearout Indicator
            '177',  # Wear Leveling Count
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
            elif 'PercentageUsed' in info:
                values['ssd_health'] = 100 - info['PercentageUsed']

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
