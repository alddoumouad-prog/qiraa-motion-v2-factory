#!/usr/bin/env python3
"""Fail closed if golden creative assets/layout code differ from the approved profile.

This is a reproducibility check, not a security boundary: a repository maintainer
can deliberately update the profile and its hashes after approving a new design.
"""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent.parent

def verify(root=ROOT):
    root=Path(root).resolve();path=root/'assets/brand/brand_manifest.json'
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('profile_id')!='qiraa-motion-v2-golden-1':raise ValueError('Unexpected brand profile')
    if not manifest.get('files'):raise ValueError('Brand lock manifest has no assets')
    mismatches=[]
    for relative,expected in manifest['files'].items():
        p=(root/relative).resolve()
        if not p.is_relative_to(root) or not p.is_file():mismatches.append(relative+' (missing)');continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:mismatches.append(relative+' (changed)')
    if mismatches:raise ValueError('Golden brand verification failed: '+', '.join(mismatches))
    return manifest['profile_id']
