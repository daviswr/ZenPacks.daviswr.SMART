# ZenPacks.daviswr.SMART

ZenPack to model & monitor storage devices' S.M.A.R.T. status

## Requirements

* [smartmontools](https://www.smartmontools.org/)
  * Should work with versions 6.x and 7.x
  * Potentially limited functionality with 5.x
* An account on the host, which can
  * Log in via SSH with a key
  * Run the `smartctl` command with certain parameters via privilege escalation without password
    * This may not be required on some hosts, depending on configuration
    * Currently tries to detect `dzdo`, `doas`, `pfexec`, and `sudo`
* [ZenPackLib](https://help.zenoss.com/in/zenpack-catalog/open-source/zenpacklib)

Example entries in `/etc/sudoers`

```
Cmnd_Alias SMARTCTL = /usr/sbin/smartctl --info *
zenoss ALL=(ALL) NOPASSWD: SMARTCTL
```
## zProperties
* `zSmartDiskMapMatch`
  * Regex of device names for the modeler to match. If unset, there is no filtering, and all discovered devices (see below) are modeled.
* `zSmartIgnoreModels`
  * Regex of model names for the modeler to ignore. For SCSI devices with separate Vendor and Product fields, this compared against Vendor and Product joined with a space.
* `zSmartIgnoreUnsupported`
  * Skips modeling of devices reported to not support SMART. Defaults to True.

## Discovery
On systems other than macOS, SMART-supporting devices are discovered with `smartctl --scan`.

This pack will **not** attempt to enable SMART on any device using `smartctl --smart=on` or set any other parameter. Configuration of smartmon is outside the scope of this pack and document.

### macOS
Due to the device name format that `smartctl --scan` returns on macOS, devices are discovered using `diskutil list` instead and results found not to support SMART are ignored.

### Linux
NVMe devices may not be reported by `smartctl --scan`, so discovery by `ls /dev/nvme*` is also attempted.

### Manual
Devices on HP Smart Arrays using the CCISS driver may not be reported by `smartctl --scan`. Those and other non-reporting devices may be added manually to `zenoss_smart.txt` in the home directory of the account used by Zenoss to access the target system. Entries should be one device per line, in the format of `smartctl --scan` output.

Example:
```
/dev/sda -d cciss,1
/dev/sdb -d cciss,2
/dev/sdc -d cciss,3
```

## Datapoints & Graphs
Percentages come from the normalized "Value" columns as reported by `smartctl --attributes`. Values in excess of 100 are scaled to 0-100.

If a normalized value is at or below a non-zero threshold as reported by `smartctl --attributes`, an event is generated. This is not based on thresholds in the performance template.

Some normalized health values may not be available on SCSI/SAS or NVMe devices, based on limitations of `smartctl` output.

### Health Score Graph
#### Rated Lifetime
The normalized value of whichever of the following attributes is found first:
* 9 - Power On Hours
* 193 - Load Cycle Count
* 225 - Load/Unload Cycle Count
* 12 - Power Cycle Count

Failing that, percentage of accumulated load-unload cycles vs lifetime specified, or accumulated start-stop cycles vs lifetime specified.

#### Read Errors
The normalized value for `Raw_Read_Error_Rate` (1).

#### Reallocated Sectors
The normalized value for `Reallocated_Sector_Ct` (5).

#### SSD Life
The normalized value of whichever of the following attributes is found first:
* 169 - Remaining Life Percentage
* 202 - Percent Lifetime Remain / Data Address Mark Errors
* 173 - Ave Block-Erase Count / Wear Leveling Count / Media Wearout Indicator
* 177 - Wear Leveling Count / Wear Range Delta
* 231 - SSD Life Left

Failing that, the `Percentage Used Endurance Indicator` value from Device Stats or `Percentage Used` from NVMe information is subtracted from 100.

#### Overall
Lowest normalized value reported that is NOT:
* Temperature
* 0 value with 0 threshold
* Used in the Rated Lifetime datapoint
* Used in the SSD Life datapoint

### Reallocated Sectors Graph
Current raw value counts for `Reallocated_Sector_Ct` (5) and `Offline_Uncorrectable` (198). `Number of Reallocated Logical Sectors` is taken from Device Stats if `Reallocated_Sector_Ct` is not present, or `Elements in grown defect list` if Device Stats is not available.

Kingston SSDs may reset the attribute 198 counter at power-on, and consider the attribute to be "Uncorrectable Sector Count".

An event will be generated if either of these values is > 0. Increasing reallocation counts are treated as unique events that will not be deduplicated.

### Reallocation Rate Graph
Raw values for above online and offline reallocation as rates, with current raw value of `Current_Pending_Sector` (197), or `Number of Realloc. Candidate Logical Sectors` from Device Stats.

### Errors Graph
Total of `Non-medium error count` for SCSI devices, `Media and Data Integrity Errors` for NVMe devices, and `Number of Reported Uncorrectable Errors` & `Number of Interface CRC Errors` from Device Stats, as a rate.

### Activity Graph
`Blocks sent to initiato` & `Blocks received from initiator` for SCSI devices, `Data Units Read` & `Data Units Written`, or `Logical Sectors Read` & `Logical Sectors Written` from Device Stats, as rates.

### Throughput Graph
Activity Graph values multiplied by device's logical block size.

### Read/Write Commands Graph
Sum of `Number of read and write commands whose size <= segment size` & `Number of read and write commands whose size > segment size` for SCSI devices, sum of `Host Read Commands` & `Host Write Commands` for NVMe devices, or sum of `Number of Read Commands` & `Number of Write Commands` from Device Stats, as a rate.

### Temperature Graph
Current raw value for `Temperature_Celsius` (194) or `Airflow_Temperature_Cel` (190). `Current Temperature` is taken from SCT Temperature or Device Stats if neither attribute is present. Attribute 231 may be used if device is a hard disk, or 189 if it is idenfitied as Temperature.

### PHY Events Graph
Total PHY events from SCSI or SATA PHY event logs as a rate.

## Usage
I'm not going to make any assumptions about your device class organization, so it's up to you to configure the `daviswr.cmd.SMART` modeler on the appropriate class or device.

While this ZenPack tries to be as generic as possible, please keep in mind your storage device manufacturer may have chosen to use attributes in a proprietary way.

## Special Thanks
* [RageLtMan](https://github.com/sempervictus)
* [Crosse](https://github.com/Crosse)
