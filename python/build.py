#!/usr/bin/env python

from pathlib import Path
import pprint

from jinja2 import Template
from yaml import safe_load
from markdown import markdown
import requests

# concatenate yml files...

here = Path(__file__).parent.resolve()

all_path = here.parent / 'packages/all.yml'
all_path.unlink(missing_ok=True)
packages = (here.parent / 'packages').glob('*')


print("Opening section names file")
with (here.parent / 'section_names.yml').open() as f:
    section_names = safe_load(f)

section_names = section_names['section_names']

print("section_names", section_names)
packs = dict()
# divide the yml files into sections based on teh section tag...
for package in packages:
    with package.open('r') as fin:
        pack = safe_load(fin)
        if 'section' not in pack:
            pack['section'] = 'miscellaneous'
        if pack['section'] in packs:
            packs[pack['section']] += [pack]   
        else:
            packs[pack['section']] = [pack]

pprint.pprint(packs)

with all_path.open('w') as out:
    for secname in sorted(packs.keys()):
        packs_sec = sorted(packs[secname], key=lambda i: i['repo'].split('/')[1].lower())
        
        out.write(f'  - name: {section_names[secname]}\n')
        out.write(f'    packages:\n\n')
        for pack in packs_sec:
            out.write(f'    - repo: {pack["repo"]}\n')
            for k, v in pack.items():
                if k != 'repo':
                    out.write(f'      {k}: {v}\n')
        out.write('\n')
                     


print("Opening config file")
with all_path.open() as f:
    config = safe_load(f)
pprint.pprint(config)
print()

for section in config:
    print(section.get('name', ''))
    if section.get('intro'):
        section['intro'] = markdown(section['intro'])
    for package in section['packages']:
        print(f"  {package['repo']}")
        try:
            package['user'], package['repo_name'] = package['repo'].split('/')
        except:
            raise Warning('Package.repo is not in correct format', package)
            continue
        package['conda_package'] = package.get('conda_package', package['repo_name'])
        package['pypi_name'] = package.get('pypi_name', package['repo_name'])

        package['section'] = section_names[package['section'].lower()]
        if package.get('badges'):
            package['badges'] = [x.strip() for x in package['badges'].split(',')]
        else:
            package['badges'] = ['pypi', 'conda']

        needs_newline = False
        if 'pypi' in package['badges']:
            needs_newline = True
            print('    pypi: ', end='', flush=True)
            response = requests.get(
                f"https://pypi.org/pypi/{package['pypi_name']}/json/")
            if response.status_code == 200:
                print('found')
            else:
                print('not found')
                package['badges'].remove('pypi')
        if package.get('conda_channel') and 'conda' not in package['badges']:
            package['badges'].append('conda')
        if 'conda_channel' not in package:
            package['conda_channel'] = 'conda-forge'
        if 'conda' in package['badges']:
            needs_newline = True
            print('    conda: ', end='')
            response = requests.get(
                f"https://anaconda.org/{package['conda_channel']}/{package['conda_package']}/",
                allow_redirects=False)
            if response.status_code == 200:
                print('found', end='')
            else:
                print('not found', end='')
                package['badges'].remove('conda')
        if needs_newline:
            print()

        if package.get('sponsors') and 'sponsor' not in package['badges']:
            package['badges'].append('sponsor')
        if package.get('site') and 'site' not in package['badges'] and 'rtd' not in package['badges']:
            package['badges'].append('site')
        if package.get('dormant') and 'dormant' not in package['badges']:
            package['badges'].append('dormant')
        

        if 'rtd' in package['badges'] and 'rtd_name' not in package:
            package['rtd_name'] = package['repo_name']

        if 'site' in package['badges']:
            if 'site' not in package:
                package['site'] = '{}.org'.format(package['repo_name'])
                package['site_protocol'] = 'https'
            else:
                package['site_protocol'], package['site'] = package['site'].rstrip('/').split('://')

template = Template((here / 'template.rst').read_text())

config = sorted(config, key = lambda i: i['name'])


(here.parent / 'docs/source/packages.rst').write_text(f"""\
Third-party and user-contributed packages
=========================================

.. include:: intro.rst

{template.render(config=config)}
""")
