#!/usr/bin/env python3
"""Read-only layout checks. Never import automotive code or access hardware."""
from pathlib import Path
import ast
import json
import subprocess
import sys


def check(root):
    manifest = json.loads((root / 'docs/path-migration.json').read_text(encoding='utf-8'))
    errors = []
    for target in manifest['paths'].values():
        if not (root / target).is_file():
            errors.append('Datei fehlt: ' + target)
    for old, entry in manifest['compatibility'].items():
        p = root / old
        if not p.is_file():
            errors.append('Einstieg fehlt: ' + old)
            continue
        body = p.read_text(encoding='utf-8')
        if entry['target'] not in body:
            errors.append('Falsches Weiterleitungsziel: ' + old)
        if old.endswith('.py'):
            try:
                ast.parse(body, filename=old)
            except SyntaxError as exc:
                errors.append(str(exc))
    for path in ['platform/launcher/launch_kodi.sh', 'platform/launcher/launch_hudiy.sh',
                 'platform/launcher/mira_splash.py', 'platform/boot/mira-animation/theme/frame-0.png',
                 'scripts/features.conf']:
        if not (root / path).is_file():
            errors.append('Laufzeitressource fehlt: ' + path)
    private = subprocess.run(['git', 'ls-files', '--', 'scripts/hudiy_api/'], cwd=root,
                             text=True, capture_output=True)
    if private.returncode:
        errors.append('Git-Bestand konnte nicht geprüft werden: ' + private.stderr.strip())
    elif private.stdout.strip():
        errors.append('Private HUDIY-Dateien sind versioniert; vor Veröffentlichung prüfen.')
    return errors


if __name__ == '__main__':
    errors = check(Path(__file__).resolve().parents[1])
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    print('Struktur und Kompatibilitätseinstiege vollständig. Kein Hardwaretest ausgeführt.')
