#pylint: disable=line-too-long,no-init,invalid-name,too-few-public-methods
""" Models SMART-supporting storage devices via SSH """

import re

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin
from Products.DataCollector.plugins.DataMaps import MultiArgs, ObjectMap

from ZenPacks.daviswr.SMART.lib.util import (
    SMART_DISABLED,
    SMART_ENABLED,
    vendor_dict
    )


class SMART(CommandPlugin):
    """ Models SMART-supporting storage devices via SSH """

    relname = 'smartStorage'
    modname = 'ZenPacks.daviswr.SMART.SmartStorage'

    # On macOS, a 'smartctl --scan' result looks like
    # IOService:/AppleACPIPlatformExpert/PCI0@0/AppleACPIPCI/SATA@1F,2/
    # AppleAHCI/PRT2@2/IOAHCIDevice@0/AppleAHCIDiskDriver/
    # IOAHCIBlockStorageDevice
    command_raw = r"""$ZENOTHING;
        smart_path=$(command -v smartctl);
        if [[ $smart_path != *smartctl ]];
        then
            smart_path=$(whereis smartctl | cut -d' ' -f2);
        fi;
        smart_opts="--badsum=ignore --nocheck=standby";
        if [[ $(uname -s) == "Darwin" ]];
        then
            scan_cmd="/usr/sbin/diskutil list | grep physical | cut -d' ' -f1";
        else
            scan_cmd="$smart_path --scan $smart_opts | cut -d' ' -f1";
        fi;
        health_cmd="$smart_path --health $smart_opts";
        for device in $(eval $scan_cmd);
        do
            info_cmd="$smart_path --info --get=all --capabilities $smart_opts";
            permission=$(eval $health_cmd $device | tail -1);
            if [[ $permission == *Permission\ denied ]];
            then
                info_cmd="sudo $info_cmd";
            fi;
            if [[ $permission != *Operation\ not\ supported\ by\ device ]];
            then
                echo "Device Path: $device";
                eval $info_cmd $device;
                echo "--------";
            fi;
        done"""
    command = ' '.join(command_raw.replace('    ', '').splitlines())

    def process(self, device, results, log):
        """ Generates RelationshipMaps from Command output """

        log.info(
            'Modeler %s processing data for device %s',
            self.name(),
            device.id
            )

        match_re = getattr(device, 'zSmartDiskMapMatch', '')
        if match_re:
            log.debug('%s: zSmartDiskMapMatch set to %s', device.id, match_re)
        else:
            log.debug('%s: zSmartDiskMapMatch not set', device.id)

        # Example:     512 bytes logical, 4096 bytes physical
        sector_re = r'(\d+) bytes logical, (\d+) bytes physical'

        rm = self.relMap()

        """ Example output

        Device Path: /dev/sde
        smartctl 6.6 2016-05-31 r4324 [x86_64-linux-4.9.0-8-amd64] (local build)  # noqa
        Copyright (C) 2002-16, Bruce Allen, Christian Franke, www.smartmontools.org  # noqa

        Smartctl open device: /dev/sde failed: Permission denied
        smartctl 6.6 2016-05-31 r4324 [x86_64-linux-4.9.0-8-amd64] (local build)  # noqa
        Copyright (C) 2002-16, Bruce Allen, Christian Franke, www.smartmontools.org  # noqa

        === START OF INFORMATION SECTION ===
        Model Family:     Western Digital Red
        Device Model:     WDC WD40EFRX-68N32N0
        Serial Number:    WD-WCC7K3KCRH5F
        LU WWN Device Id: 5 0014ee 265155ff0
        Firmware Version: 82.00A82
        User Capacity:    4,000,787,030,016 bytes [4.00 TB]
        Sector Sizes:     512 bytes logical, 4096 bytes physical
        Rotation Rate:    5400 rpm
        Form Factor:      3.5 inches
        Device is:        In smartctl database [for details use: -P show]
        ATA Version is:   ACS-3 T13/2161-D revision 5
        SATA Version is:  SATA 3.1, 6.0 Gb/s (current: 3.0 Gb/s)
        Local Time is:    Tue Oct 26 13:11:33 2021 EDT
        SMART support is: Available - device has SMART capability.
        SMART support is: Enabled
        Power mode is:    ACTIVE or IDLE

        --------
        Device Path: /dev/disk5
        smartctl 7.2 2020-12-30 r5155 [Darwin 19.6.0 x86_64] (local build)
        Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org  # noqa

        Smartctl open device: /dev/disk5 failed: Operation not supported by device  # noqa
        """

        devices = results.split('--------')

        for dev in devices:
            dev_map = dict()

            for line in dev.splitlines():
                if ': ' in line and 'capability' not in line:
                    key_raw, value_raw = line.replace(' is', '').split(':', 1)
                    key = ''
                    for term in key_raw.strip().replace('-', ' ').split(' '):
                        key += term.title()
                    value = value_raw.strip()
                    # Various cleanup
                    if '.' == value[-1]:
                        value = value[0:-1]
                    if 'bytes' in value:
                        try:
                            value = int(value.split(' ')[0].replace(',', ''))
                        except ValueError:
                            continue
                    if 'Sector Size' in key_raw:
                        match = re.search(sector_re, value_raw)
                        if match:
                            log_sect, phys_sect = match.groups()
                            dev_map['LogicalSector'] = int(log_sect)
                            dev_map['PhysicalSector'] = int(phys_sect)
                        else:
                            dev_map['LogicalSector'] = value
                            dev_map['PhysicalSector'] = value
                    elif 'Logical block size' in key_raw:
                        dev_map['LogicalSector'] = value
                    elif 'Physical block size' in key_raw:
                        dev_map['PhysicalSector'] = value
                    elif key in ['SataVersion', 'TransportProtocol']:
                        dev_map['TransportType'] = value
                    elif key_raw == 'SMART support':
                        value = (SMART_ENABLED if 'Enabled' in value
                                 else SMART_DISABLED)
                    elif key_raw.startswith('AAM'):
                        key = 'AamFeature'
                    elif key_raw.startswith('APM'):
                        key = 'ApmFeature'
                    dev_map[key] = value

            if 'DevicePath' in dev_map:
                if match_re and not re.search(match_re, dev_map['DevicePath']):
                    log.info(
                        '%s: %s ignored due to zSmartDiskMapMatch',
                        device.id,
                        dev_map['DevicePath']
                        )
                else:
                    dev_map['title'] = dev_map['DevicePath'].split('/')[-1]
                    dev_map['id'] = self.prepId(dev_map['title'])
                    om = ObjectMap(modname=self.modname, data=dev_map)
                    model = dev_map.get('DeviceModel', '').replace('_', ' ')
                    if model:
                        if ' ' in model:
                            vendor, model = model.split(' ', 1)
                            vendor = vendor_dict.get(vendor, vendor.title())
                        else:
                            vendor = vendor_dict.get(model[0:2], 'Unknown')
                        om.setProductKey = MultiArgs(model, vendor)
                    rm.append(om)

        log.debug('%s RelMap:\n%s', self.name(), str(rm))
        return rm
