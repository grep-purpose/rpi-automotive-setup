import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path

import xbmc
import xbmcgui

HOME = xbmcgui.Window(10000)
REPO = "/home/pi/rpi-automotive-setup"

def setprop(name, value):
    if value is None or value == "":
        value = "-"

    value = str(value).replace("\n", " ").strip()

    HOME.setProperty(
        "RNSE.SysInfo." + name,
        value
    )

def run(cmd):
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3
        ).strip()
    except Exception:
        return ""

def read(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return ""

def pretty_bytes(value):
    try:
        value = float(value)
    except Exception:
        return "-"

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return "%.1f %s" % (value, unit)
        value /= 1024

    return "%.1f PB" % value

def interface_ip(name):
    result = run(
        "ip -4 -o addr show dev %s | awk '{print $4}' | head -n1"
        % name
    )

    return result or "-"

def interface_state(name):
    value = read(
        "/sys/class/net/%s/operstate" % name
    )

    return value or "nicht vorhanden"

def net_stat(name, stat):
    return read(
        "/sys/class/net/%s/statistics/%s" % (name, stat)
    ) or "0"

# ------------------------------------------------------------
# NETZWERK
# ------------------------------------------------------------

ssid = run(
    "nmcli -t -f GENERAL.CONNECTION device show wlan0 "
    "| cut -d: -f2-"
)

signal = run(
    "nmcli -t -f IN-USE,SIGNAL device wifi list "
    "| awk -F: '$1==\"*\" {print $2; exit}'"
)

gateway = run(
    "ip route | awk '/default/ {print $3; exit}'"
)

dns = ""

try:
    for line in Path("/etc/resolv.conf").read_text().splitlines():
        if line.startswith("nameserver "):
            dns = line.split()[1]
            break
except Exception:
    pass

setprop("SSID", ssid)
setprop("Signal", (signal + " %") if signal else "-")
setprop("WLANIP", interface_ip("wlan0"))
setprop("EthernetIP", interface_ip("eth0"))
setprop("Gateway", gateway)
setprop("DNS", dns)

# ------------------------------------------------------------
# RASPBERRY PI
# ------------------------------------------------------------

temp = read("/sys/class/thermal/thermal_zone0/temp")

try:
    temp = "%.1f °C" % (int(temp) / 1000)
except Exception:
    temp = "-"

freq = read(
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
)

try:
    freq = "%.0f MHz" % (int(freq) / 1000)
except Exception:
    freq = "-"

try:
    load1, load5, load15 = os.getloadavg()
    load = "%.2f / %.2f / %.2f" % (
        load1,
        load5,
        load15
    )
except Exception:
    load = "-"

meminfo = {}

try:
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        meminfo[key] = int(value.strip().split()[0]) * 1024
except Exception:
    pass

mem_total = meminfo.get("MemTotal", 0)
mem_avail = meminfo.get("MemAvailable", 0)
mem_used = max(0, mem_total - mem_avail)

swap_total = meminfo.get("SwapTotal", 0)
swap_free = meminfo.get("SwapFree", 0)
swap_used = max(0, swap_total - swap_free)

disk = shutil.disk_usage("/")

uptime_raw = read("/proc/uptime")

try:
    sec = int(float(uptime_raw.split()[0]))

    days, sec = divmod(sec, 86400)
    hours, sec = divmod(sec, 3600)
    minutes, sec = divmod(sec, 60)

    parts = []

    if days:
        parts.append("%d d" % days)

    if hours:
        parts.append("%d h" % hours)

    parts.append("%d min" % minutes)

    uptime = " ".join(parts)
except Exception:
    uptime = "-"

throttle = run(
    "command -v vcgencmd >/dev/null && vcgencmd get_throttled"
)

setprop("Temp", temp)
setprop("CPUFreq", freq)
setprop("Load", load)

setprop(
    "RAM",
    "%s / %s" % (
        pretty_bytes(mem_used),
        pretty_bytes(mem_total)
    )
)

setprop(
    "Swap",
    "%s / %s" % (
        pretty_bytes(swap_used),
        pretty_bytes(swap_total)
    )
)

setprop(
    "Disk",
    "%s frei von %s" % (
        pretty_bytes(disk.free),
        pretty_bytes(disk.total)
    )
)

setprop("Uptime", uptime)
setprop("Throttle", throttle or "-")

# ------------------------------------------------------------
# SYSTEM
# ------------------------------------------------------------

os_name = ""

try:
    for line in Path("/etc/os-release").read_text().splitlines():
        if line.startswith("PRETTY_NAME="):
            os_name = line.split("=", 1)[1].strip().strip('"')
            break
except Exception:
    pass

setprop("Hostname", socket.gethostname())
setprop("OS", os_name)
setprop("Kernel", platform.release())
setprop("Arch", platform.machine())

# ------------------------------------------------------------
# KODI
# ------------------------------------------------------------

setprop(
    "KodiVersion",
    xbmc.getInfoLabel("System.BuildVersion")
)

try:
    setprop("Skin", xbmc.getSkinDir())
except Exception:
    setprop("Skin", "-")

setprop(
    "KodiWindow",
    xbmc.getInfoLabel("System.CurrentWindow")
)

# ------------------------------------------------------------
# AUTOMOTIVE / CAN
# ------------------------------------------------------------

setprop("CAN0State", interface_state("can0"))
setprop("VCAN0State", interface_state("vcan0"))

bitrate = run(
    "ip -details link show can0 "
    "| grep -o 'bitrate [0-9]*' "
    "| head -n1 | awk '{print $2}'"
)

if bitrate:
    try:
        bitrate = "%d kbit/s" % (int(bitrate) // 1000)
    except Exception:
        pass

setprop("CAN0Bitrate", bitrate)

rx = net_stat("can0", "rx_packets")
tx = net_stat("can0", "tx_packets")

setprop(
    "CAN0Packets",
    "%s RX / %s TX" % (rx, tx)
)

hudiy = run(
    "pgrep -fa hudiy | head -n1"
)

setprop(
    "HUDIY",
    "aktiv" if hudiy else "nicht aktiv"
)

# ------------------------------------------------------------
# GIT / PROJEKT
# ------------------------------------------------------------

branch = run(
    "git -C '%s' branch --show-current" % REPO
)

commit = run(
    "git -C '%s' rev-parse --short HEAD" % REPO
)

status = run(
    "git -C '%s' status --porcelain" % REPO
)

setprop("GitBranch", branch)
setprop("GitCommit", commit)

setprop(
    "GitStatus",
    "sauber" if not status else "Änderungen vorhanden"
)
