#pylint: disable=line-too-long,no-init,invalid-name,too-few-public-methods
""" Models SMART-supporting storage devices via SSH """

import re

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin
from Products.DataCollector.plugins.DataMaps import MultiArgs, ObjectMap

from ZenPacks.daviswr.SMART.lib.util import vendor_dict


class SMART(CommandPlugin):
    """ Models SMART-supporting storage devices via SSH """

    relname = 'smartStorage'
    modname = 'ZenPacks.daviswr.SMART.SmartStorage'

    deviceProperties = CommandPlugin.deviceProperties + (
        'zSmartDiskMapMatch',
        'zSmartIgnoreModels',
        'zSmartIgnoreUnsupported',
        )

    # On macOS, a 'smartctl --scan' result looks like
    # IOService:/AppleACPIPlatformExpert/PCI0@0/AppleACPIPCI/SATA@1F,2/
    # AppleAHCI/PRT2@2/IOAHCIDevice@0/AppleAHCIDiskDriver/
    # IOAHCIBlockStorageDevice
    # On Linux, 'smartctl --scan' may not show NVMe devices
    command_raw = r"""$ZENOTHING;
        IFS=$(echo -en "\n\b");
        smart_path=$(command -v smartctl);
        if [[ $smart_path != *smartctl ]];
        then
            smart_path=$(whereis smartctl | cut -d' ' -f2);
        fi;
        smart_opts="--badsum=ignore --nocheck=standby";
        if [[ $(uname -s) == Darwin ]];
        then
            scan_cmd="/usr/sbin/diskutil list | grep physical | cut -d' ' -f1";
            scan_cmd="$scan_cmd | sed 's~\$~ -d auto~g'";
        else
            scan_cmd="$smart_path --scan $smart_opts | cut -d'#' -f1";
            scan_cmd="$scan_cmd | sed 's~-d scsi \|ata ~-d auto~g'";
        fi;
        if [[ $(uname -s) == Linux ]];
        then
            scan_cmd="$scan_cmd ; ls /dev/nvme* 2>/dev/null";
            scan_cmd="$scan_cmd | grep -e 'nvme[[:digit:]]\$'";
            scan_cmd="$scan_cmd | sed 's~\$~ -d auto~g'";
        fi;
        scan_cmd="$scan_cmd ; cat ~/zenoss_smart.txt 2>/dev/null";
        health_cmd="$smart_path --health $smart_opts";
        for device in $(eval $scan_cmd);
        do
            device=$(echo $device | sed 's~-d ~--device ~g');
            info_cmd="$smart_path --info --get=all --capabilities $smart_opts";
            permission=$(eval $health_cmd $device | tail -1);
            if [[ $permission == *Permission\ denied ]];
            then
                for priv_cmd in dzdo doas pfexec sudo;
                do
                    if [[ -e $(command -v $priv_cmd) ]];
                    then
                        break;
                    fi;
                done;
                info_cmd="$priv_cmd $info_cmd";
            fi;
            if [[ $permission != *Operation\ not\ supported\ by\ device ]];
            then
                echo "Device Path: $device";
                eval $info_cmd $device;
                echo "--------";
            fi;
        done"""
    command = ' '.join(command_raw.replace('  ', '').splitlines())

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

        skip_models_re = getattr(device, 'zSmartIgnoreModels', '')
        if skip_models_re:
            log.debug(
                '%s: zSmartIgnoreModels set to %s',
                device.id,
                skip_models_re
                )
        else:
            log.debug('%s: zSmartIgnoreModels not set', device.id)

        skip_unsupport = getattr(device, 'zSmartIgnoreUnsupported', True)
        if skip_unsupport:
            log.debug('%s: zSmartIgnoreUnsupported set', device.id)
        else:
            log.debug('%s: zSmartIgnoreUnsupported not set', device.id)

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
        indexed = dict()
        block = dict()
        dedupe = list()

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
                    elif 'Formatted LBA Size' in key_raw:
                        dev_map['LogicalSector'] = value
                    elif key in ['SataVersion', 'TransportProtocol']:
                        dev_map['TransportType'] = value
                    elif 'Total NVM Capacity' in key_raw:
                        dev_map['UserCapacity'] = value
                    elif (key in ['Product', 'ModelNumber']
                            and 'DeviceModel' not in dev_map):
                        dev_map['DeviceModel'] = value
                    elif key_raw == 'SMART support':
                        # This comes from a datapoint rather
                        # than modeled attribute
                        continue
                    dev_map[key] = value

            if (dev_map.get('DevicePath', None)
                    and dev_map.get('SerialNumber', None)):
                dev_path = dev_map['DevicePath']
                # Model fixup for SCSI devices
                if dev_map.get('Vendor', None) and dev_map.get('Product', None):
                    if not dev_map['Product'].startswith(dev_map['Vendor']):
                        dev_map['DeviceModel'] = '{0} {1}'.format(
                            dev_map['Vendor'],
                            dev_map['Product']
                            )
                # Ignore criteria
                # zSmartDiskMapMatch
                if match_re and not re.search(match_re, dev_path):
                    log.info(
                        '%s: %s ignored due to zSmartDiskMapMatch',
                        device.id,
                        dev_path
                        )
                    continue
                # zSmartIgnoreModels
                elif (re.search(skip_models_re, dev_map.get('DeviceModel', ''))
                      and skip_models_re):
                    log.info(
                        '%s: %s ignored due to zSmartIgnoreModels',
                        device.id,
                        dev_path
                        )
                    continue
                # zSmartIgnoreUnsupported
                elif (('Unavailable - device lacks SMART capability' in dev
                        or 'Operation not supported by device' in dev)
                        and skip_unsupport):
                    log.info(
                        '%s: %s does not support SMART, ignoring',
                        device.id,
                        dev_path
                        )
                    continue
                else:
                    if '-d' in dev_path and dev_path.endswith('auto'):
                        block_dev = dev_path.split(' ', 1)[0]
                        dev_map['BlockDevice'] = block_dev.replace('/dev/', '')
                        block[dev_map['SerialNumber']] = dev_map
                    # Indexed drive on a controller/HBA/DAS/etc
                    else:
                        indexed[dev_map['SerialNumber']] = dev_map
            else:
                # Lacks Device Path or Serial Number
                continue

        # Deduplicate serials
        for serial in indexed:
            if serial in block:
                # All other properties should be the same
                indexed[serial]['BlockDevice'] = block[serial]['BlockDevice']
                del block[serial]
            else:
                block_dev = indexed[serial]['DevicePath'].split(' ', 1)[0]
                indexed[serial]['BlockDevice'] = block_dev
            dedupe.append(indexed[serial])
        for serial in block:
            dedupe.append(block[serial])

        for dev_map in dedupe:
            dev_map['title'] = dev_map['DevicePath'].replace('--device', '-d')
            dev_map['title'] = dev_map['title'].replace(' -d auto', '')
            dev_map['id'] = self.prepId(dev_map['SerialNumber'])
            # NVMe form-factor
            if 'FormFactor' not in dev_map:
                for form in ['M.2', 'U.2']:
                    if form in dev_map.get('DeviceModel', ''):
                        dev_map['FormFactor'] = form
                        break
            # Best guess block size if we failed to get it
            if 'LogicalSector' not in dev_map:
                dev_map['LogicalSector'] = 512
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
