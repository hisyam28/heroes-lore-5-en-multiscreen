#!/usr/bin/env python3
"""Check project metadata, public files and documentation without game inputs."""
from pathlib import Path
import ast
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'.apk', '.aab', '.zip', '.jar', '.ipa', '.dex', '.so', '.a',
             '.keystore', '.jks', '.key', '.pem', '.p12', '.pfx', '.idsig'}
PUBLIC_DIRS = {'config', 'docs', 'tools', 'tests', 'translations', 'reports'}
ROOT_FILES = {'README.md', 'CREDITS.md', 'AGENTS.md', '.gitignore', '.gitattributes'}


def public_files():
    proc = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT, capture_output=True)
    if proc.returncode == 0 and proc.stdout:
        return [ROOT / name.decode('utf-8') for name in proc.stdout.split(b'\0') if name]
    return [p for p in ROOT.rglob('*') if p.is_file() and
            (p.relative_to(ROOT).parts[0] in PUBLIC_DIRS or p.relative_to(ROOT).as_posix() in ROOT_FILES)]


def main():
    project = json.loads((ROOT / 'config/project.json').read_text(encoding='utf-8'))
    target = json.loads((ROOT / 'config/target-profile.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT / 'translations/catalog.json').read_text(encoding='utf-8'))
    if project['project'] != 'heroes-lore-5-en' or project['target_language'] != 'en':
        raise ValueError('Unexpected project identity')
    fingerprint = target['apk_sha256']
    if fingerprint is not None and not re.fullmatch('[0-9a-f]{64}', fingerprint):
        raise ValueError('Invalid target APK SHA-256')
    if catalog['entries'] and (fingerprint is None or catalog['target_apk_sha256'] != fingerprint):
        raise ValueError('Catalog must match an identified target APK')
    if target['status'] == 'unverified' and target['verified_patches']:
        raise ValueError('Unverified target cannot contain verified patches')
    checked = 0
    for path in public_files():
        relative = path.relative_to(ROOT)
        name = relative.as_posix()
        if name in {'inputs/.gitkeep', 'work/.gitkeep', 'dist/.gitkeep'}:
            continue
        if relative.parts[0] not in PUBLIC_DIRS and name not in ROOT_FILES:
            raise ValueError('Unexpected tracked path: ' + name)
        if path.suffix.lower() in FORBIDDEN:
            raise ValueError('Private/binary input in public source: ' + name)
        text = path.read_text(encoding='utf-8-sig')
        patterns = [r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})',
                    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                    r'(?i)\b[A-Z]:[\\/]Users[\\/]', r'https?://[^\s/@]+:[^\s/@]+@']
        if any(re.search(pattern, text) for pattern in patterns):
            raise ValueError('Credential or private path found: ' + name)
        if path.suffix == '.json':
            json.loads(text)
        elif path.suffix == '.py':
            ast.parse(text, filename=name)
        elif path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if '://' in link or link.startswith('#'):
                    continue
                destination = (path.parent / link.split('#')[0]).resolve()
                if not destination.is_relative_to(ROOT) or not destination.exists():
                    raise ValueError('Broken documentation link: ' + name + ' -> ' + link)
        checked += 1
    print(f'Workspace check passed: {checked} public files; project status: {project["status"]}.')


if __name__ == '__main__':
    main()
