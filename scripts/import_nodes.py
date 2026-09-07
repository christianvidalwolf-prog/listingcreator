"""Import Amazon.es nodes from columns B/C of a MAPPINGS workbook (requires xlrd)."""
import argparse
import hashlib
import json
from pathlib import Path
import xlrd


def import_catalog(source, destination):
    source = Path(source)
    sheet = xlrd.open_workbook(source).sheet_by_name('MAPPINGS')
    if sheet.cell_value(0, 1) != 'Node ID' or sheet.cell_value(0, 2) != 'Node Path':
        raise ValueError('Se esperaban Node ID y Node Path en las columnas B y C')
    nodes = []
    seen = set()
    for i in range(1, sheet.nrows):
        root, raw_id, raw_path = sheet.row_values(i)[:3]
        if isinstance(raw_id, float) and raw_id.is_integer():
            node_id = str(int(raw_id))
        else:
            node_id = str(raw_id).strip()
        path = str(raw_path).strip()
        if not node_id.isdigit() or not path.startswith('/Categorías/') or not str(root).startswith('es-'):
            raise ValueError(f'Fila {i + 1} inválida')
        key = (node_id, path, root)
        if key in seen:
            continue
        seen.add(key)
        nodes.append({'id': node_id, 'path': path, 'root': root})
    catalog = {'source': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'sheet': 'MAPPINGS', 'marketplace': 'Amazon.es', 'id_column': 'B',
               'path_column': 'C', 'source_rows': sheet.nrows - 1, 'nodes': nodes}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(catalog, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(nodes)} rutas y {len({n["id"] for n in nodes})} identificadores importados en {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination', nargs='?', default=str(Path(__file__).resolve().parents[1] / 'api/data/amazon_nodes.json'))
    args = parser.parse_args()
    import_catalog(args.source, args.destination)
