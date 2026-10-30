import importlib.util
import fcntl
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.modules.setdefault("xbmc", types.SimpleNamespace(
    log=Mock(), LOGERROR=4))
sys.modules.setdefault("xbmcgui", types.SimpleNamespace(
    Window=Mock(), Dialog=Mock(), WindowXMLDialog=object, ListItem=Mock(),
    NOTIFICATION_INFO=0, NOTIFICATION_ERROR=3))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load("mira_dpi", ROOT / "apps/kodi/userdata/scripts/mira_android_auto_settings.py")
installer = load("installer", ROOT / "tools/install_mira_android_auto_settings.py")


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.config = self.home / ".hudiy/share/config/main_configuration.json"
        self.config.parent.mkdir(parents=True)
        self.original = {
            "androidAuto": {"dpi": 150, "width": 784, "height": 468,
                            "x": 10, "y": 0, "widthMargin": 16, "heightMargin": 12},
            "application": {"width": 784},
            "private": {"password": "keep-this-local"}
        }
        self.config.write_text(json.dumps(self.original))
        self.raw = self.config.read_bytes()

    def test_change_preserves_every_other_setting_and_backup(self):
        with patch.object(helper, "hudiy_running", return_value=False):
            self.assertTrue(helper.save_dpi(self.config, 190, 150))
        expected = json.loads(self.raw)
        expected["androidAuto"]["dpi"] = 190
        self.assertEqual(json.loads(self.config.read_text()), expected)
        saved = list((self.config.parent / "mira-dpi-backups").glob("*.json"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), self.raw)
        self.assertEqual(saved[0].stat().st_mode & 0o777, 0o600)

    def test_invalid_values_never_write(self):
        for value in (139, 201, 145, True, "150"):
            with self.assertRaises(ValueError):
                helper.save_dpi(self.config, value, 150)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_running_hudiy_never_writes(self):
        with patch.object(helper, "hudiy_running", return_value=True):
            with self.assertRaises(RuntimeError):
                helper.save_dpi(self.config, 160, 150)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_hudiy_start_during_write_is_rejected(self):
        with patch.object(helper, "hudiy_running", side_effect=[False, True]):
            with self.assertRaises(RuntimeError):
                helper.save_dpi(self.config, 160, 150)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_concurrent_dpi_change_rejected(self):
        with patch.object(helper, "hudiy_running", return_value=False):
            with self.assertRaises(RuntimeError):
                helper.save_dpi(self.config, 170, 140)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_same_value_no_backup_no_write(self):
        with patch.object(helper, "hudiy_running", return_value=False):
            self.assertFalse(helper.save_dpi(self.config, 150, 150))
        self.assertFalse((self.config.parent / "mira-dpi-backups").exists())
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_cancel_does_not_save_and_current_is_preselected(self):
        with patch.object(helper, "CONFIG", self.config), \
             patch.object(helper, "synchronize", return_value=150), \
             patch.object(helper, "hudiy_running", return_value=False), \
             patch.object(helper, "choose_dpi", return_value=None) as choose, \
             patch.object(helper, "save_dpi") as save, \
             patch.object(sys, "argv", ["script", "select"]):
            helper.main()
            save.assert_not_called()
        choose.assert_called_once_with(150)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_popup_preselects_saved_value_and_lists_seven_rows(self):
        dialog = helper.DPIWindow()
        dialog.configure(150)
        control = Mock()
        with patch.object(dialog, "getControl", return_value=control, create=True), \
             patch.object(dialog, "setFocusId", create=True) as focus:
            dialog.onInit()
        self.assertEqual(control.addItem.call_count, 7)
        control.selectItem.assert_called_once_with(1)
        focus.assert_called_once_with(9500)

    def test_busy_old_lock_does_not_block_opening_or_cancel(self):
        lock_path = self.config.parent / ".mira-dpi.lock"
        with lock_path.open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(helper, "CONFIG", self.config), \
                 patch.object(helper, "synchronize", return_value=150), \
                 patch.object(helper, "hudiy_running", return_value=False), \
                 patch.object(helper, "choose_dpi", return_value=None) as choose, \
                 patch.object(sys, "argv", ["script", "select"]):
                helper.main()
                choose.assert_called_once_with(150)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_busy_save_reports_error_instead_of_silent_return(self):
        lock_path = self.config.parent / ".mira-dpi.lock"
        with lock_path.open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(helper, "CONFIG", self.config), \
                 patch.object(helper, "synchronize", return_value=150), \
                 patch.object(helper, "hudiy_running", return_value=False), \
                 patch.object(helper, "choose_dpi", return_value=160), \
                 patch.object(sys, "argv", ["script", "select"]):
                with self.assertRaisesRegex(RuntimeError, "belegt"):
                    helper.main()
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_failed_save_releases_short_lock(self):
        with patch.object(helper, "CONFIG", self.config), \
             patch.object(helper, "synchronize", return_value=150), \
             patch.object(helper, "hudiy_running", return_value=False), \
             patch.object(helper, "choose_dpi", return_value=160), \
             patch.object(helper, "save_dpi", side_effect=OSError("write failed")), \
             patch.object(sys, "argv", ["script", "select"]):
            with self.assertRaises(OSError):
                helper.main()
        with (self.config.parent / ".mira-dpi.lock").open("r") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(stream, fcntl.LOCK_UN)

    def test_popup_return_cancels_and_click_returns_selected_value(self):
        dialog = helper.DPIWindow()
        dialog.configure(150)
        control = Mock()
        control.getSelectedPosition.return_value = 6
        with patch.object(dialog, "getControl", return_value=control, create=True), \
             patch.object(dialog, "close", create=True) as close:
            dialog.onClick(9500)
            self.assertEqual(dialog.value, 200)
            close.assert_called_once()
            for action_id in (9, 10, 92):
                action = Mock()
                action.getId.return_value = action_id
                dialog.onAction(action)
                self.assertIsNone(dialog.value)

    def test_install_and_rollback_preserve_configuration(self):
        settings = self.home / ".kodi/userdata/guisettings.xml"
        settings.parent.mkdir(parents=True)
        settings.write_text('<settings><setting id="lookandfeel.skin">'
                            'skin.estuary.custom</setting></settings>')
        xml = self.home / ".kodi/addons/skin.estuary.custom/xml/custom_Display.xml"
        xml.parent.mkdir(parents=True)
        original = (ROOT / "tests/display-before.xml").read_bytes()
        xml.write_bytes(original)
        backup = installer.install(self.home, ROOT)
        tree = ET.fromstring(xml.read_text())
        items = tree.findall(".//content/item")
        self.assertEqual(items[0].findtext("label"), "Android Auto")
        self.assertEqual(items[0].findtext("onclick"), installer.ACTION)
        self.assertEqual(installer.patched_xml(xml.read_text()), xml.read_text())
        self.assertEqual(self.config.read_bytes(), self.raw)
        script = self.home / ".kodi/userdata/scripts" / installer.SCRIPT
        self.assertTrue(script.exists())
        self.assertTrue((script.parent / installer.FOCUS).is_file())
        installer.restore(backup, self.home)
        self.assertEqual(xml.read_bytes(), original)
        self.assertFalse(script.exists())
        self.assertFalse((script.parent / installer.FOCUS).exists())
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_unrecognized_menu_rejected(self):
        with self.assertRaises(ValueError):
            installer.patched_xml('<window id="1157"><defaultcontrol>1</defaultcontrol></window>')

    def test_upgrade_rollback_restores_previous_helper(self):
        settings = self.home / ".kodi/userdata/guisettings.xml"
        settings.parent.mkdir(parents=True)
        settings.write_text('<settings><setting id="lookandfeel.skin">'
                            'skin.estuary.custom</setting></settings>')
        xml = self.home / ".kodi/addons/skin.estuary.custom/xml/custom_Display.xml"
        xml.parent.mkdir(parents=True)
        original = installer.patched_xml((ROOT / "tests/display-before.xml").read_text())
        xml.write_text(original)
        script = self.home / ".kodi/userdata/scripts" / installer.SCRIPT
        script.parent.mkdir(parents=True)
        script.write_text("# previous working DPI helper\n")
        before = script.read_bytes()
        backup = installer.install(self.home, ROOT)
        self.assertNotEqual(script.read_bytes(), before)
        installer.restore(backup, self.home)
        self.assertEqual(script.read_bytes(), before)
        self.assertEqual(xml.read_text(), original)
        self.assertFalse((script.parent / installer.RESOURCE).exists())
        self.assertFalse((script.parent / installer.FOCUS).exists())
        self.assertEqual(self.config.read_bytes(), self.raw)


if __name__ == "__main__":
    unittest.main()
