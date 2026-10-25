"""Recreate lossless paper-fixture extraction; no scientific computation.

Requires openpyxl only for workbook parsing. Publisher originals are downloaded
only with --download; existing files are validated against downloads.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def extract(source_name, output_name, sheet, columns, labels, doi, scope,
            member=None, bounds=None):
    from openpyxl import load_workbook
    source = ROOT / 'sources' / source_name
    data = source.read_bytes()
    archive_hash = sha256(data)
    if member:
        with ZipFile(io.BytesIO(data)) as archive:
            data = archive.read(member)
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    rows, source_rows = [], []
    for index, row in enumerate(workbook[sheet].iter_rows(values_only=True), 1):
        x, y = (row[column] for column in columns)
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        if bounds and not bounds[0] <= x <= bounds[1]:
            continue
        rows.append((x, y))
        source_rows.append(index)
    workbook.close()
    output = ROOT / 'data' / output_name
    output.parent.mkdir(exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(labels)
        writer.writerows(rows)
    receipt = {
        'paper_doi': doi,
        'source_file': str(source.relative_to(ROOT)),
        'source_sha256': archive_hash,
        'sheet': sheet,
        'coordinate_column': chr(65 + columns[0]),
        'value_column': chr(65 + columns[1]),
        'selection': f'{bounds[0]} <= depth_m <= {bounds[1]}; numeric cells only; source row order unchanged'
        if bounds else 'All numeric rows, source order unchanged',
        'source_row_numbers': source_rows,
        'output_file': str(output.relative_to(ROOT)),
        'output_sha256': sha256(output.read_bytes()),
        'row_count': len(rows),
        'transformations': 'None. Python only extracts workbook cells and selects an explicit interval where specified; no resampling, detrending, spectral calculation or plot.',
        'scope': scope,
    }
    if member:
        receipt.update(archive_member=member, member_sha256=sha256(data))
    output.with_suffix('.provenance.json').write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return receipt


def extract_lavernock():
    """Copy untuned height and raw susceptibility; exclude PANGAEA sentinels."""
    source = ROOT / 'sources/weedon_lavernock_2018.tsv'
    rows, source_lines = [], []
    header_seen = False
    for number, line in enumerate(source.read_text(encoding='utf-8').splitlines(), 1):
        if line.startswith('Strat height [m]\t'):
            header_seen = True
            continue
        if not header_seen:
            continue
        cells = line.split('\t')
        try:
            height, susceptibility = float(cells[0]), float(cells[3])
        except (ValueError, IndexError):
            continue
        if 0 <= height <= 13.17 and susceptibility != -9999:
            rows.append((height, susceptibility))
            source_lines.append(number)
    output = ROOT / 'data/weedon_2020_lavernock_0_13_17m.csv'
    with output.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['stratigraphic_height_m', 'magnetic_susceptibility_1e-6_SI'])
        writer.writerows(rows)
    receipt = {
        'paper_doi': '10.21701/bolgeomin.131.2.001',
        'method_origin_doi': '10.1017/S0016756818000808',
        'dataset_doi': '10.1594/PANGAEA.896872',
        'source_file': str(source.relative_to(ROOT)),
        'source_url': 'https://doi.pangaea.de/10.1594/PANGAEA.896872?format=textfile',
        'source_sha256': sha256(source.read_bytes()),
        'coordinate_column': 'Strat height [m]',
        'value_column': 'MAGS [10**-6 SI]',
        'selection': '0 <= stratigraphic_height_m <= 13.17; exclude dataset missing-value sentinel -9999; source row order unchanged',
        'source_line_numbers': source_lines,
        'output_file': str(output.relative_to(ROOT)),
        'output_sha256': sha256(output.read_bytes()),
        'row_count': len(rows),
        'actual_coordinate_range_m': [min(x for x, _ in rows), max(x for x, _ in rows)],
        'license': 'CC-BY-4.0, https://creativecommons.org/licenses/by/4.0/',
        'transformations': 'Selected columns and rows only; no tuned ages, E-filter output, interpolation, detrending, spectrum or plot calculation.',
        'scope': 'Untuned Lavernock MS from the SWA method data deposit, restricted to the interval analysed in Weedon (2020), Fig. 11. The published 0.0–13.17 m interval has actual deposited observations at 0.03–13.17 m.',
    }
    output.with_suffix('.provenance.json').write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    for record in json.loads((ROOT / 'sources/downloads.json').read_text()):
        path = ROOT / record['file']
        if not path.is_file():
            if not args.download:
                raise SystemExit(f'Missing {path}; use --download to fetch the recorded publisher source')
            with urllib.request.urlopen(record['source_url'], timeout=120) as response:
                data = response.read()
            if sha256(data) != record['sha256']:
                raise SystemExit(f'Publisher content changed: {path.name}')
            path.write_bytes(data)
        if sha256(path.read_bytes()) != record['sha256']:
            raise SystemExit(f'Source checksum mismatch: {path}')
    records = [
        extract('petm_2022_source.xlsx', 'petm_2022_ms_194_200m.csv', 'Ca & MS',
                (3, 4), ['depth_m', 'magnetic_susceptibility_SI_x1e-5'],
                '10.1038/s41467-022-33390-x',
                'Paper-data workflow smoke test on a selected 6 m interval, not reproduction of the published Lomb-Scargle/COCO/ASM analysis.',
                bounds=(194, 200)),
        extract('petm_2022_source.xlsx', 'petm_2022_ms_below_nanjemoy.csv', 'Ca & MS',
                (3, 4), ['depth_m', 'magnetic_susceptibility_SI_x1e-5'],
                '10.1038/s41467-022-33390-x',
                'Untuned MS below the Nanjemoy basal unconformity. The lower bound comes from the Lithology information sheet, Nanjemoy Formation depth (m); the upper bound is the deepest numeric MS observation. Modern Acycle COCO rate-consistency comparison, not exact Acycle 2.4.1 paper reproduction.',
                bounds=(187.50380981408108, 214.558)),
        extract('petm_2022_source.xlsx', 'petm_2022_ms_published_coco_interval.csv', 'Ca & MS',
                (3, 4), ['depth_m', 'magnetic_susceptibility_SI_x1e-5'],
                '10.1038/s41467-022-33390-x',
                'Independent protocol-corrected fixture from Supplementary Text 3, pp. 22–23: raw file interval encoded as 187.54–211.24 m. Python only selects these raw observations. The published 187.542–211.232 m, 2370-point series follows MATLAB 20 m LOESS and linear interpolation at 0.01 m; it is not the raw fixture. Preserve the earlier broader-interval comparison separately.',
                bounds=(187.54, 211.24)),
        extract('cambrian_2022_source.zip', 'cambrian_2022_gamma_ray.csv',
                'GR_Albjära-1 core', (0, 1), ['depth_m', 'gamma_ray_counts_per_second'],
                '10.1038/s41467-022-29651-4',
                'Workflow smoke test on published auxiliary gamma-ray record; not reproduction of the paper primary Al-based astrochronology.',
                member='S4. Gamma-ray log_Albjära-1 core.xlsx'),
        extract('cambrian_2022_source.zip', 'cambrian_2022_al_0_18m.csv',
                'Merged XRF data', (0, 2), ['adjusted_depth_m', 'aluminium_percent'],
                '10.1038/s41467-022-29651-4',
                'Primary untuned Al proxy, first published depth subset. Uses author-adjusted depth, not the astronomically tuned age column. Intended for a reduced-budget modern eCOCO workflow; the full paper uses additional smoothing, full-record detrending, a much denser window step and 5000 simulations.',
                member='S2. Merged XRF data_Albjära-1 core (used in this study).xlsx',
                bounds=(0, 18)),
        extract_lavernock(),
    ]
    print(json.dumps([{'file': r['output_file'], 'sha256': r['output_sha256'],
                       'rows': r['row_count']} for r in records], indent=2))


if __name__ == '__main__':
    main()
