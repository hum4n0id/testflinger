# Device Firmware Upgrade Tool

This is the prototype for firmware upgrade test. It will be temporarily placed in `/extras` folder until we figure out a proper way to merge it into device agent codes. 
Currently, it only supports `fwupd/LVFS` update method on selected device types (DMI chassis type = All In One, Desktop) with selected OEM (HP, Dell, and Lenovo). Note that it hasn't be widely tested on all supported devices.

## How to use this tool directly
### Upgrade all firmware on the DUT to the latest version.
`$ upgrade_fw.py upgrade $DEVICE_IP`

### Downgrade all firmware on the DUT to the 2nd new version.
`$ upgrade_fw.py upgrade $DEVICE_IP`

### Detect DUT type and all updatable firmware, no upgrade/downgrade will be performed.
`$ upgrade_fw.py detect $DEVICE_IP`

### All usages:
`$ upgrade_fw.py --help`

## Log and output
All logs (including commands output) can be found at `/tmp/upgrade_fw.log`

## Use this tool with Testflinger
Testflinger job yaml file example.
```
job_queue: <TF job queue name>
provision_data:
test_data:
        test_cmds: |
          sudo apt update && sudo apt install -y git
          git clone -b main https://github.com/canonical/testflinger.git
          cd testflinger/extras
          ./upgrade_fw.py upgrade $DEVICE_IP
          sudo cat /tmp/upgrade_fw.log
reserve_data:
```

### Unit test and code coverage
```
$ python -m pip install coverage pytest pytest-cov
# cd to testflinger/extras
$ python -m coverage run -m pytest .
```