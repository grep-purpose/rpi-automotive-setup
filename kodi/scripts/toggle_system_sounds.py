import json
import sys
import xbmc

SETTING = "audiooutput.guisoundmode"
STATE = "RNSE.SystemSoundsState"

# Kodi GUI sound modes:
# 0 = Never
# 1 = Only when playback is stopped
# 2 = Always
OFF_VALUE = 0
ON_VALUE = 2


def rpc(method, params=None):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method
    }

    if params is not None:
        request["params"] = params

    raw = xbmc.executeJSONRPC(json.dumps(request))

    try:
        result = json.loads(raw)
    except Exception:
        result = {}

    xbmc.log(
        "RNSE SystemSounds RPC: %s" % raw,
        xbmc.LOGINFO
    )

    return result


def get_value():
    response = rpc(
        "Settings.GetSettingValue",
        {
            "setting": SETTING
        }
    )

    return response.get(
        "result",
        {}
    ).get(
        "value"
    )


def set_value(value):
    response = rpc(
        "Settings.SetSettingValue",
        {
            "setting": SETTING,
            "value": value
        }
    )

    return "error" not in response


def is_enabled():
    value = get_value()

    try:
        return int(value) != OFF_VALUE
    except Exception:
        return False


def update_checkbox():
    if is_enabled():
        xbmc.executebuiltin(
            "Skin.SetString(%s,on)" % STATE
        )
    else:
        xbmc.executebuiltin(
            "Skin.SetString(%s,off)" % STATE
        )


def toggle():
    current = get_value()

    xbmc.log(
        "RNSE SystemSounds current guisoundmode: %s"
        % current,
        xbmc.LOGINFO
    )

    try:
        current = int(current)
    except Exception:
        current = OFF_VALUE

    if current == OFF_VALUE:
        target = ON_VALUE
    else:
        target = OFF_VALUE

    success = set_value(target)

    xbmc.log(
        "RNSE SystemSounds target=%s success=%s"
        % (target, success),
        xbmc.LOGINFO
    )

    xbmc.sleep(250)

    update_checkbox()


mode = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "sync"
)

if mode == "toggle":
    toggle()
else:
    update_checkbox()
