#!/usr/bin/python3
"""The main program to trigger firmware upgrading/downgrading on a DUT"""

import subprocess
import argparse
import logging
import sys
from dmi import Dmi
from devices import *

SSH_OPTS = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
target_device_username = "ubuntu"


def all_subclasses(cls):
    return cls.__subclasses__() + [
        g for s in cls.__subclasses__() for g in all_subclasses(s)
    ]


def detect_device(
    ip: str, user: str, password: str = "", **options
) -> AbstractDevice:
    """
    Detect device's firmware upgrade type by checking on DMI data

    :ip:        DUT IP
    :user:      DUT user
    :password:  DUT password (default=blank)
    :return:    device class object
    :rtype:     an instance of a class that implements AbstractDevice
    """
    temp_device = LVFSDevice(ip, user, password)
    run_ssh = temp_device.run_cmd
    devices = all_subclasses(AbstractDevice)
    try:
        dmi_chassis_vendor = "sudo cat /sys/class/dmi/id/chassis_vendor"
        dmi_chassis_type = "sudo cat /sys/class/dmi/id/chassis_type"
        rc1, vendor_string, stderr1 = run_ssh(
            dmi_chassis_vendor, raise_stderr=False
        )
        rc2, type_string, stderr2 = run_ssh(
            dmi_chassis_type, raise_stderr=False
        )

        err_msg = ""
        if rc1 != 0:
            err_msg = vendor_string + stderr1 + "\n"
        if rc2 != 0:
            err_msg = err_msg + type_string + stderr2
        if err_msg:
            err_msg = (
                "Unable to detect device vendor/type due to lacking of dmi info.\n"
                + err_msg
            )
            logger.error(err_msg)
            sys.exit(err_msg)

        type_index = int(type_string)
        upgrade_type = Dmi.chassis_types[type_index]
        try:
            dev = [
                dev
                for dev in devices
                if dev.fw_update_type in upgrade_type
                and any(x == vendor_string for x in dev.vendor)
            ][0]
            logger.info("%s is a %s %s", ip, vendor_string, dev.__name__)
        except IndexError:
            err_msg = f"{vendor_string} {Dmi.chassis_names[type_index]} Device is not in current support scope"
            logger.error(err_msg)
            sys.exit(err_msg)

        if issubclass(dev, LVFSDevice):
            return dev(ip, user, password)
        elif issubclass(dev, OEMDevice):
            if not (
                "bmc_ip" in options
                and "bmc_user" in options
                and "bmc_password" in options
            ):
                sys.exit(
                    "Please provide $BMC_IP, $BMC_USER, $BMC_PASSWORD for this device"
                )
            return dev(
                options.get("bmc_ip"),
                options.get("bmc_user"),
                options.get("bmc_password"),
            )
    except subprocess.CalledProcessError as e:
        logger.error(e.output)
        raise RuntimeError(e.output)


def main():
    """
    mandantory parameter: $DEVICE_IP (testflinger env variable)
    extra parameters for Server: $BMC_IP, $BMC_USERNAME, $BMC_PASSWORD
    (not yet provided by testflinger)
    """
    parser = argparse.ArgumentParser(
        epilog="Example: %(prog)s upgrade 10.0.0.1",
        usage="%(prog)s {upgrade, downgrade, detect} $DEVICE_IP [options]",
    )
    parser.add_argument(
        choices=["upgrade", "downgrade", "detect"],
        dest="action",
        help="select to upgrade firmware, downgrade firmware, or just detect DUT info without further actions",
    )
    parser.add_argument("device_ip", help="$DEVICE_IP")
    parser.add_argument(
        "--bmc-ip",
        "-i",
        nargs="?",
    )
    parser.add_argument(
        "--bmc-user",
        "-u",
        nargs="?",
    )
    parser.add_argument(
        "--bmc-password",
        "-p",
        nargs="?",
    )
    args = parser.parse_args()

    log_file = "/tmp/upgrade_fw.log"
    logger.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%y-%m-%d %H:%M:%S",
        filename=log_file,
        filemode="w",
    )

    if args.bmc_ip and args.bmc_user and args.bmc_password:
        target_device = detect_device(
            args.device_ip,
            target_device_username,
            bmc_ip=args.bmc_ip,
            bmc_user=args.bmc_user,
            bmc_password=args.bmc_password,
        )
    else:
        target_device = detect_device(
            args.device_ip, target_device_username, password="insecure"
        )

    target_device.get_fw_info()
    if args.action == "detect":
        print(f"Check {log_file} for details.")
        return
    if args.action == "upgrade":
        reboot_required = target_device.upgrade()
    else:
        reboot_required = target_device.downgrade()
    if reboot_required:
        target_device.reboot()
        target_device.check_results()
    else:
        print(f"Firmware {args.action} is not performed.")
    print(f"Check {log_file} for more details.")


if __name__ == "__main__":
    main()
