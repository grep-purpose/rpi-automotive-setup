#!/usr/bin/env python3

import json
import os
import sys
import time
from pathlib import Path

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib


AGENT_PATH = "/com/rnse/BluetoothAgent"

RUNTIME_DIR = Path("/run/user/1000")
STATE_FILE = RUNTIME_DIR / "rnse_bt_pairing_state.json"
DECISION_FILE = RUNTIME_DIR / "rnse_bt_pairing_decision"

BLUEZ_SERVICE = "org.bluez"
AGENT_MANAGER = "/org/bluez"


def write_state(**data):
    payload = {
        "timestamp": time.time(),
        **data,
    }

    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    tmp.replace(STATE_FILE)


def clear_decision():
    try:
        DECISION_FILE.unlink()
    except FileNotFoundError:
        pass


def wait_for_decision(timeout=60):
    clear_decision()

    deadline = time.time() + timeout

    while time.time() < deadline:
        if DECISION_FILE.exists():
            try:
                decision = (
                    DECISION_FILE
                    .read_text()
                    .strip()
                    .lower()
                )
            finally:
                clear_decision()

            if decision == "approve":
                return True

            if decision == "reject":
                return False

        time.sleep(0.2)

    return False


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Canceled(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Canceled"


class Agent(dbus.service.Object):

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="",
        out_signature="",
    )
    def Release(self):
        write_state(
            status="released",
            message="Pairing-Agent wurde freigegeben",
        )

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="o",
        out_signature="s",
    )
    def RequestPinCode(self, device):
        write_state(
            status="unsupported",
            mode="pin",
            device=str(device),
            message="PIN-Eingabe wird derzeit nicht unterstützt",
        )

        raise Rejected(
            "PIN-Eingabe wird derzeit nicht unterstützt"
        )

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="o",
        out_signature="u",
    )
    def RequestPasskey(self, device):
        write_state(
            status="unsupported",
            mode="passkey_input",
            device=str(device),
            message="Passkey-Eingabe wird derzeit nicht unterstützt",
        )

        raise Rejected(
            "Passkey-Eingabe wird derzeit nicht unterstützt"
        )

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="os",
        out_signature="",
    )
    def DisplayPinCode(self, device, pincode):
        write_state(
            status="display",
            mode="pin_display",
            device=str(device),
            code=str(pincode),
        )

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="ouq",
        out_signature="",
    )
    def DisplayPasskey(
        self,
        device,
        passkey,
        entered,
    ):
        write_state(
            status="display",
            mode="passkey_display",
            device=str(device),
            code=f"{int(passkey):06d}",
            entered=int(entered),
        )

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="ou",
        out_signature="",
    )
    def RequestConfirmation(
        self,
        device,
        passkey,
    ):
        code = f"{int(passkey):06d}"

        write_state(
            status="confirmation_required",
            mode="confirmation",
            device=str(device),
            code=code,
            message="Pairing-Code bestätigen",
        )

        if wait_for_decision():
            write_state(
                status="confirmation_approved",
                mode="confirmation",
                device=str(device),
                code=code,
            )
            return

        write_state(
            status="confirmation_rejected",
            mode="confirmation",
            device=str(device),
            code=code,
        )

        raise Rejected("Pairing abgelehnt")

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="os",
        out_signature="",
    )
    def AuthorizeService(
        self,
        device,
        uuid,
    ):
        return

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="o",
        out_signature="",
    )
    def RequestAuthorization(self, device):
        write_state(
            status="authorization_required",
            mode="authorization",
            device=str(device),
            message="Gerät möchte gekoppelt werden",
        )

        if wait_for_decision():
            return

        raise Rejected("Pairing abgelehnt")

    @dbus.service.method(
        "org.bluez.Agent1",
        in_signature="",
        out_signature="",
    )
    def Cancel(self):
        write_state(
            status="canceled",
            message="Pairing wurde abgebrochen",
        )


def main():
    if len(sys.argv) != 2:
        print(
            "Verwendung: bluetooth_pair_agent.py "
            "AA:BB:CC:DD:EE:FF"
        )
        return 2

    mac = sys.argv[1].upper()

    device_path = (
        "/org/bluez/hci0/dev_"
        + mac.replace(":", "_")
    )

    clear_decision()

    try:
        STATE_FILE.unlink()
    except FileNotFoundError:
        pass

    dbus.mainloop.glib.DBusGMainLoop(
        set_as_default=True
    )

    bus = dbus.SystemBus()

    agent = Agent(bus, AGENT_PATH)

    manager_obj = bus.get_object(
        BLUEZ_SERVICE,
        AGENT_MANAGER,
    )

    manager = dbus.Interface(
        manager_obj,
        "org.bluez.AgentManager1",
    )

    device_obj = bus.get_object(
        BLUEZ_SERVICE,
        device_path,
    )

    device = dbus.Interface(
        device_obj,
        "org.bluez.Device1",
    )

    props = dbus.Interface(
        device_obj,
        "org.freedesktop.DBus.Properties",
    )

    loop = GLib.MainLoop()

    try:
        manager.RegisterAgent(
            AGENT_PATH,
            "DisplayYesNo",
        )

        manager.RequestDefaultAgent(
            AGENT_PATH
        )

    except dbus.DBusException as exc:
        write_state(
            status="error",
            message=f"Agent konnte nicht registriert werden: {exc}",
        )
        return 1

    write_state(
        status="starting",
        mac=mac,
        device=device_path,
        message="Pairing wird gestartet",
    )

    def pair_success():
        try:
            props.Set(
                "org.bluez.Device1",
                "Trusted",
                dbus.Boolean(True),
            )
        except Exception:
            pass

        write_state(
            status="paired",
            mac=mac,
            device=device_path,
            message="Gerät erfolgreich gekoppelt",
        )

        GLib.timeout_add(
            500,
            lambda: (
                loop.quit(),
                False,
            )[1],
        )

    def pair_error(error):
        write_state(
            status="error",
            mac=mac,
            device=device_path,
            message=str(error),
        )

        GLib.timeout_add(
            500,
            lambda: (
                loop.quit(),
                False,
            )[1],
        )

    GLib.idle_add(
        lambda: (
            device.Pair(
                reply_handler=pair_success,
                error_handler=pair_error,
            ),
            False,
        )[1]
    )

    try:
        loop.run()

    finally:
        try:
            manager.UnregisterAgent(
                AGENT_PATH
            )
        except Exception:
            pass

        clear_decision()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
