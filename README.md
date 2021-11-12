# ZenPacks.daviswr.SMART

ZenPack to model & monitor storage devices' S.M.A.R.T. status

## Requirements

* [smartmontools](https://www.smartmontools.org/)
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

## Discovery notes
On systems other than macOS, SMART-supporting devices are discovered with `smartctl --scan`. Due to the device name format that command returns on macOS, devices are discovered using `diskutil list` instead and results found not to support SMART are ignored. Neither of these commands should require elevated privileges.

This pack will **not** attempt to enable SMART on any device using `smartctl --smart=on`. Configuration of smartmon is outside the scope of this pack and document.

## Usage
### Modelers
I'm not going to make any assumptions about your device class organization, so it's up to you to configure the `daviswr.cmd.SMART` modeler on the appropriate class or device. 

## Special Thanks
* [RageLtMan](https://github.com/sempervictus)
