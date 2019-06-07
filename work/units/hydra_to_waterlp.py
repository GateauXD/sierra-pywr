import json

with open('hydra_units.json', 'r') as f:
    hydra_dims = json.load(f)

units_dict = {}
units = {}
for hydra_dim in hydra_dims:

    dim = hydra_dim['name']

    for hydra_unit in hydra_dim['unit']:
        concise_unit = {
            'lf': float(hydra_unit['lf']),
            'cf': float(hydra_unit['cf']),
            'dim': dim
            # 'info': hydra_unit.get('info', '')
        }
        uabbr = hydra_unit['abbr']
        uname = hydra_unit['name']
        if uabbr in units:
            print('Unit {} already exists for {}. Skipping'.format(uabbr, dim))
            continue
        if uname in units:
            if uname == 'No unit':
                uname = uabbr
            else:
                print('Unit {} already exists for {}. Skipping'.format(uname, dim))
                continue
        units[uabbr] = concise_unit
        units[uname] = concise_unit

with open('waterlp_units.json', 'w') as f:
    json.dump(units, f, ensure_ascii=False, indent=4, separators=(',', ': '))