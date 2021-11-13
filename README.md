# ZenPacks.daviswr.SMART

ZenPack to model & monitor storage devices' S.M.A.R.T. status

## Requirements

* [smartmontools](https://www.smartmontools.org/)
  * Should work with versions 6.x and 7.x
  * Limited functionality with 5.x
* An account on the host, which can
  * Log in via SSH with a key
  * Run the `smartctl` command with certain parameters without password via `sudo` - This may not be required on some hosts, depending on configuration
* [ZenPackLib](https://help.zenoss.com/in/zenpack-catalog/open-source/zenpacklib)

Example entries in `/etc/sudoers`

```
Cmnd_Alias SMARTCTL = /usr/sbin/smartctl --info *
zenoss ALL=(ALL) NOPASSWD: SMARTCTL
```
## zProperties
* `zSmartDiskMapMatch`
  * Regex of device names for the modeler to match. If unset, there is no filtering, and all discovered devices (see below) are modeled.

## Discovery
On systems other than macOS, SMART-supporting devices are discovered with `smartctl --scan`. Due to the device name format that command returns on macOS, devices are discovered using `diskutil list` instead and results found not to support SMART are ignored. Neither of these commands should require elevated privileges.

This pack will **not** attempt to enable SMART on any device using `smartctl --smart=on` or set any other parameter. Configuration of smartmon is outside the scope of this pack and document.

## Datapoints & Graphs
Percentages come from the normalized "Value" columns as reported by `smartctl`. Values in excess of 100 are scaled to 0-100.

If a normalized value is at or below a non-zero threshold as reported by `smartctl`, an event is generated. This is not based on thresholds in the performance template.

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

### Reallocation Rate Graph
Raw values for `Reallocated_Sector_Ct` (5) and `Offline_Uncorrectable` (198) as rates, with current raw value of `Current_Pending_Sector` (197).

### Temperature Graph
Current raw value for `Temperature_Celsius` (194) or `Airflow_Temperature_Cel` (190). `Current Temperature` is taken from SCT Temperature or Device Stats if neither attribute is present. Attribute 231 may be used if device is a hard disk, or 189 if it is idenfitied as Temperature.

## Usage
I'm not going to make any assumptions about your device class organization, so it's up to you to configure the `daviswr.cmd.SMART` modeler on the appropriate class or device.

While this ZenPack tries to be as generic as possible, please keep in mind your storage device manufacturer may have chosen to use attributes in a proprietary way.

## Special Thanks
* [RageLtMan](https://github.com/sempervictus)
