"""Inventário estático: lê AST/texto; nunca importa ou executa o aplicativo.

Lê os arquivos rastreados direto dos objetos do Git numa revisão (padrão:
HEAD), então o resultado corresponde a um commit, não à árvore de trabalho.
Gera, ao lado deste script, `INVENTARIO.json` e `ROTAS.md`.

    python3 -I docs/about/build_inventory.py            # revisão HEAD
    python3 -I docs/about/build_inventory.py --rev 1.4-criptografia

Adaptado da versão que lia uma cópia (`source-1.4/` + `SOURCE_MANIFEST.json`)
obtida pela API do GitHub: aqui a lista de arquivos, o SHA de cada blob e o
tamanho vêm de `git ls-tree -r -l`, e a integridade é conferida recalculando o
SHA do blob lido.
"""
from pathlib import Path
import argparse
import ast
import collections
import hashlib
import json
import re
import subprocess

BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent
REPOSITORY = 'G4TTI/Attena-Assistant'

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument('--rev', default='HEAD', help='commit, branch ou tag a inventariar (padrão: HEAD)')
args = parser.parse_args()

def git(*cmd):
    return subprocess.run(['git', '-C', str(REPO), *cmd], check=True, capture_output=True).stdout

SHA = git('rev-parse', '--verify', args.rev + '^{commit}').decode().strip()
manifest = {'files': []}
for line in git('ls-tree', '-r', '-l', '--full-tree', SHA).decode().splitlines():
    meta, path = line.split('\t', 1)
    mode, kind, blob, size = meta.split()
    if kind == 'blob':
        manifest['files'].append({'path': path, 'sha': blob, 'size': int(size)})

inventory = {'repository': REPOSITORY, 'commit': SHA,
             'method': 'Análise estática AST/texto dos blobs do Git, sem importar app nem executar testes.',
             'files': [], 'functions': [], 'classes': [], 'routes': [],
             'templates': [], 'test_definitions': [], 'integrity_mismatches': []}

def expr(n):
    return ast.unparse(n) if n is not None else None

class Visitor(ast.NodeVisitor):
    def __init__(self, path, router_prefixes, router_dependencies):
        self.path = path
        self.scope = []
        self.prefixes = router_prefixes
        self.dependencies = router_dependencies

    def visit_ClassDef(self, node):
        fields = [s.target.id for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
        inventory['classes'].append({'file': self.path, 'line': node.lineno,
            'name': '.'.join(self.scope + [node.name]), 'bases': [expr(x) for x in node.bases],
            'fields': fields, 'keywords': {x.arg: expr(x.value) for x in node.keywords}})
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self.function(node)

    def visit_AsyncFunctionDef(self, node):
        self.function(node)

    def function(self, node):
        test = self.path.startswith('app/tests/')
        record = {'file': self.path, 'line': node.lineno, 'end_line': node.end_lineno,
            'name': '.'.join(self.scope + [node.name]), 'async': isinstance(node, ast.AsyncFunctionDef),
            'signature': expr(node.args), 'returns': expr(node.returns),
            'decorators': [expr(d) for d in node.decorator_list]}
        inventory['functions'].append(record)
        if test and node.name.startswith('test_'):
            inventory['test_definitions'].append(record)
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if dec.func.attr not in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'api_route'):
                continue
            if not isinstance(dec.func.value, ast.Name) or not dec.args or not isinstance(dec.args[0], ast.Constant):
                continue
            router = dec.func.value.id
            if router not in self.prefixes:
                continue
            kw = {k.arg: expr(k.value) for k in dec.keywords}
            methods = [dec.func.attr.upper()]
            if dec.func.attr == 'api_route':
                methods = ast.literal_eval(next(k.value for k in dec.keywords if k.arg == 'methods'))
            for method in methods:
                inventory['routes'].append({'method': method, 'path': self.prefixes[router] + dec.args[0].value,
                    'file': self.path, 'line': dec.lineno, 'handler': record['name'],
                    'signature': record['signature'], 'returns': record['returns'],
                    'router_dependencies': self.dependencies.get(router, []), 'options': kw})
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

for item in manifest['files']:
    path = item['path']
    raw = git('cat-file', 'blob', item['sha'])
    blob_sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob_sha != item['sha'] or len(raw) != item['size']:
        inventory['integrity_mismatches'].append(path)
    frec = {'path': path, 'git_blob_sha': item['sha'], 'actual_blob_sha': blob_sha, 'bytes': len(raw)}
    try:
        txt = raw.decode('utf-8')
    except UnicodeDecodeError:
        frec['binary'] = True
        inventory['files'].append(frec)
        continue
    frec['lines'] = len(txt.splitlines())
    if path.endswith('.py'):
        tree = ast.parse(txt, filename=path)
        prefixes = {}
        dependencies = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
                name = expr(n.value.func)
                if name in ('APIRouter', 'FastAPI'):
                    for target in n.targets:
                        if isinstance(target, ast.Name):
                            prefixes[target.id] = next((k.value.value for k in n.value.keywords if k.arg == 'prefix'), '')
                            dependencies[target.id] = [expr(k.value) for k in n.value.keywords if k.arg == 'dependencies']
        frec['imports'] = [expr(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        Visitor(path, prefixes, dependencies).visit(tree)
    if path.endswith('.html'):
        inventory['templates'].append({'file': path,
            'extends_includes': re.findall(r'{%\s*(?:extends|include|import|from)\s+[\'\"]([^\'\"]+)', txt),
            'htmx_attributes': sorted(set(re.findall(r'(hx-[\w-]+)=[\'\"]([^\'\"]+)', txt))),
            'named_js_functions': re.findall(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', txt)})
    inventory['files'].append(frec)

app_functions = [x for x in inventory['functions'] if not x['file'].startswith('app/tests/')]
inventory['summary'] = {
    'tracked_files': len(inventory['files']),
    'application_python_files': sum(x['path'].startswith('app/whatsapp_scheduler/') and x['path'].endswith('.py') for x in inventory['files']),
    'python_functions_and_methods': len(app_functions),
    'application_classes': sum(not x['file'].startswith('app/tests/') for x in inventory['classes']),
    'declared_http_routes': len(inventory['routes']),
    'rest_routes_under_api': sum(x['path'].startswith('/api/') for x in inventory['routes']),
    'templates': len(inventory['templates']),
    'named_inline_js_functions': sum(len(x['named_js_functions']) for x in inventory['templates']),
    'test_files': sum(x['path'].startswith('app/tests/test_') for x in inventory['files']),
    'test_function_definitions': len(inventory['test_definitions']),
    'sqlmodel_tables': sum(x['keywords'].get('table') == 'True' for x in inventory['classes']),
    'integrity_mismatches': len(inventory['integrity_mismatches'])}
(BASE / 'INVENTARIO.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
# Links relativos (a partir de docs/about/): funcionam no GitHub e localmente,
# inclusive quando a revisão inventariada ainda não foi enviada ao GitHub. As
# linhas valem para o commit abaixo; depois de mudar o código, gere de novo.
rows = ['# Rotas HTTP declaradas no código', '', f'Base: `{SHA}`.', '',
    'Extração estática dos decoradores e prefixos APIRouter. Inclui páginas, parciais HTMX, REST e webhook; exclui rotas automáticas do FastAPI. Não representa chamadas executadas nem validação funcional.', '',
    'Gerado por `build_inventory.py`; não edite à mão.', '',
    '| Método | Caminho | Handler | Fonte |', '|---|---|---|---|']
for r in inventory['routes']:
    link = f'../../{r["file"]}#L{r["line"]}'
    rows.append(f'| {r["method"]} | `{r["path"]}` | `{r["handler"]}` | [código]({link}) |')
(BASE / 'ROTAS.md').write_text('\n'.join(rows) + '\n')
print(json.dumps(inventory['summary'], ensure_ascii=False, indent=2))
if inventory['integrity_mismatches']:
    print('Divergências de cópia: ' + repr(inventory['integrity_mismatches']))
print('Rotas por arquivo: ' + repr(dict(collections.Counter(x['file'] for x in inventory['routes']))))
if git('status', '--porcelain', '--', 'app').strip():
    print('Aviso: há alterações locais em app/ que NÃO entram neste inventário (ele lê o commit ' + SHA[:7] + ').')
