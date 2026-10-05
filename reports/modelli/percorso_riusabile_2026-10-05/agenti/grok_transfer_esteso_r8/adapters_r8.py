"""Fail-closed notes for banks this generation does not mount.

A missing reader is a technical gap. It is not a scientific exclusion and it
does not drop a source for size or target overlap. Nothing here launches a job
or invents a compound map, a Tian control map, a Tian 2019 QC call, or guides.
"""
from __future__ import annotations


class AdapterGap(ValueError):
    """The saved bank has no reader in this wave."""


GAPS = {
    'hipsci': 'anchors and partitions are already registered; this wave does not relaunch them',
    'tian2021': 'the token control is not non-targeting until a verified map exists',
    'tian2019': 'QC was not verified and was not invented',
    'scp': 'no statistic is in this generation package',
    'ko': 'no statistic is in this generation package',
    'a549': 'no statistic is in this generation package',
    'norman2019': 'compound tokens stay blocked; no compound map was invented',
    'gse249595': 'guides are absent and were not invented',
    'k562_gwps': 'still the parent job; k562_essential is a different source and is not renamed',
    'davideferante_axis': 'that account has no axis dataset; this is access, not a source exclusion',
}


def describe(name):
    key = str(name).strip().lower().replace(' ', '').replace('-', '').replace('_', '')
    aliases = {
        'hipsci': 'hipsci',
        'tian2021': 'tian2021',
        'tian2019': 'tian2019',
        'scp': 'scp',
        'ko': 'ko',
        'a549': 'a549',
        'norman': 'norman2019',
        'norman2019': 'norman2019',
        'gse249595': 'gse249595',
        'k562': 'k562_gwps',
        'k562gwps': 'k562_gwps',
        'gwps': 'k562_gwps',
        'davideferante': 'davideferante_axis',
    }
    canonical = aliases.get(key)
    if canonical is None:
        return {
            'source': name,
            'admitted': False,
            'scientific_exclusion': False,
            'technical_gap': 'no adapter is registered for this name',
        }
    return {
        'source': canonical,
        'admitted': False,
        'scientific_exclusion': False,
        'technical_gap': GAPS[canonical],
        'same_linear_model': True,
    }


def load(name):
    """Refuse a silent zero. The caller records describe(name) and moves on."""
    raise AdapterGap(describe(name)['technical_gap'])
