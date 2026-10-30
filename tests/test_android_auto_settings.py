import importlib.util
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
    Window=Mock(), Dialog=Mock(), NOTIFICATION_INFO=0, NOTIFICATION_ERROR=3))


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
        dialog = Mock()
        dialog.select.return_value = -1
        with patch.object(helper, "CONFIG", self.config), \
             patch.object(helper, "synchronize", return_value=150), \
             patch.object(helper, "hudiy_running", return_value=False), \
             patch.object(helper.xbmcgui, "Dialog", return_value=dialog), \
             patch.object(helper, "save_dpi") as save, \
             patch.object(sys, "argv", ["script", "select"]):
            helper.main()
            save.assert_not_called()
        self.assertEqual(dialog.select.call_args.kwargs["preselect"], 1)
        self.assertEqual(len(dialog.select.call_args.args[1]), 7)
        self.assertEqual(self.config.read_bytes(), self.raw)

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
        installer.restore(backup, self.home)
        self.assertEqual(xml.read_bytes(), original)
        self.assertFalse(script.exists())
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_unrecognized_menu_rejected(self):
        with self.assertRaises(ValueError):
            installer.patched_xml('<window id="1157"><defaultcontrol>1</defaultcontrol></window>')


if __name__ == "__main__":
    unittest.main()
