"""Inventário estático: lê AST/texto; nunca importa ou executa o aplicativo.

Lê os arquivos rastreados direto dos objetos do Git numa revisão (padrão:
HEAD), então o resultado corresponde a um commit, não à árvore de trabalho.
Gera, ao lado deste script, `INVENTARIO.json`, `ROTAS.md` e um anexo
`<dominio>/INVENTARIO.md` por domínio.

    python3 -I docs/about/build_inventory.py            # revisão HEAD
    python3 -I docs/about/build_inventory.py --rev 1.4-criptografia --no-write

Adaptado da versão que lia uma cópia (`source-1.4/` + `SOURCE_MANIFEST.json`)
obtida pela API do GitHub: aqui a lista de arquivos, o SHA de cada blob e o
tamanho vêm de `git ls-tree -r -l`, e a integridade é conferida recalculando o
SHA do blob lido.

Domínios: cada arquivo, função/método, classe, rota, template e teste recebe
um domínio pelas tabelas abaixo (símbolo > seção do arquivo > arquivo). Item
sem domínio faz o script falhar: ao criar arquivo ou seção nova, atualize as
tabelas e o about.md do domínio.
"""
from pathlib import Path
import argparse
import ast
import collections
import hashlib
import json
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent
REPOSITORY = 'G4TTI/Attena-Assistant'
APP = 'app/whatsapp_scheduler/'
TPL = APP + 'web/templates/'

DOMAINS = {
    'arquitetura': 'Arquitetura', 'autenticacao': 'Autenticação', 'onboarding-dashboard': 'Onboarding e Dashboard',
    'whatsapp-conversas': 'WhatsApp e Conversas', 'configuracoes-conexoes': 'Configurações e Conexões',
    'agendamentos': 'Agendamentos', 'calendario': 'Calendário', 'planos-faturamento': 'Planos e Faturamento',
    'administracao': 'Administração', 'dados-migracoes': 'Dados e Migrações', 'privacidade': 'Privacidade',
    'interface': 'Interface', 'api': 'API REST', 'operacao': 'Operação', 'testes': 'Testes'}
# Documentação e instruções: fora dos domínios do app (exclusão justificada).
META = 'documentacao'

# Domínio principal por arquivo; chave terminada em "/" vale para a pasta.
# O prefixo mais longo vence.
FILE_DOMAINS = {
    APP + '__init__.py': 'arquitetura', APP + 'main.py': 'arquitetura', APP + 'config.py': 'arquitetura',
    APP + 'app_settings.py': 'arquitetura', APP + 'clock.py': 'arquitetura', APP + 'time_sync.py': 'arquitetura',
    APP + 'errors.py': 'arquitetura',
    APP + 'auth.py': 'autenticacao', APP + 'auth_service.py': 'autenticacao', APP + 'ratelimit.py': 'autenticacao',
    APP + 'web/auth_routes.py': 'autenticacao',
    APP + 'onboarding_service.py': 'onboarding-dashboard', APP + 'dashboard_service.py': 'onboarding-dashboard',
    APP + 'web/onboarding_routes.py': 'onboarding-dashboard', APP + 'web/dashboard_routes.py': 'onboarding-dashboard',
    APP + 'waha.py': 'whatsapp-conversas', APP + 'whatsapp_service.py': 'whatsapp-conversas',
    APP + 'chatsvc.py': 'whatsapp-conversas', APP + 'recipients.py': 'whatsapp-conversas',
    APP + 'web/settings_routes.py': 'configuracoes-conexoes', APP + 'web/whatsapp_routes.py': 'configuracoes-conexoes',
    APP + 'service.py': 'agendamentos', APP + 'scheduler.py': 'agendamentos', APP + 'timing.py': 'agendamentos',
    APP + 'recurrence.py': 'agendamentos', APP + 'schedule_views.py': 'agendamentos', APP + 'failures.py': 'agendamentos',
    APP + 'schemas.py': 'agendamentos', APP + 'media.py': 'agendamentos',
    APP + 'calendar_service.py': 'calendario', APP + 'calendar_sync.py': 'calendario',
    APP + 'calendar_schemas.py': 'calendario', APP + 'calendar_providers/': 'calendario',
    APP + 'web/calendar_routes.py': 'calendario',
    APP + 'plans.py': 'planos-faturamento', APP + 'billing/': 'planos-faturamento',
    APP + 'web/billing_routes.py': 'planos-faturamento',
    APP + 'admin/': 'administracao', APP + 'web/admin_routes.py': 'administracao',
    APP + 'models.py': 'dados-migracoes', APP + 'db.py': 'dados-migracoes', APP + 'migrations.py': 'dados-migracoes',
    APP + 'privacy.py': 'privacidade', APP + 'retention.py': 'privacidade', APP + 'crypto.py': 'privacidade',
    APP + 'log_sanitizer.py': 'privacidade', 'docs/SECURITY_AND_PRIVACY.md': 'privacidade',
    APP + 'web/': 'interface', APP + 'api/': 'api',
    APP + 'cli.py': 'operacao', 'docker-compose.yml': 'operacao', '.env.example': 'operacao', 'app/Dockerfile': 'operacao',
    'app/.dockerignore': 'operacao', 'app/requirements.txt': 'operacao', 'app/pyproject.toml': 'operacao',
    'README.md': 'operacao', '.gitignore': 'operacao', '.gitattributes': 'operacao',
    'app/tests/': 'testes', 'app/requirements-dev.txt': 'testes',
    'about.md': META, 'CLAUDE.md': META, 'docs/DOCUMENTATION_POLICY.md': META, 'docs/about/': META,
}
# Arquivos compartilhados divididos por seção ("# ---- Título ----" ou bloco
# "# ----\n# Título\n# ----"). O título mais longo que for prefixo vence.
SECTION_DOMAINS = {
    APP + 'web/routes.py': {
        'Contextos e entradas compartilhados': 'agendamentos', 'Páginas': 'interface', 'Parciais (htmx)': 'interface',
        'Agendamentos': 'agendamentos', 'Anexos': 'agendamentos',
        'Conversas': 'whatsapp-conversas', 'Conversas: painel': 'whatsapp-conversas'},
}
# Exceções por símbolo (nome qualificado no arquivo).
SYMBOL_DOMAINS = {
    (APP + 'web/routes.py', '_base_ctx'): 'interface',
    (APP + 'web/routes.py', 'page_schedules'): 'agendamentos',
    (APP + 'web/routes.py', 'page_chats'): 'whatsapp-conversas',
    (APP + 'web/routes.py', 'page_chats_session'): 'whatsapp-conversas',
}
# Templates: o documento principal da mecânica (HTMX/JS/layout) é Interface;
# aqui fica a tela/funcionalidade a que cada um serve.
TEMPLATE_FEATURES = {
    'base.html': 'interface', '_components.html': 'interface', '_sidebar_status.html': 'interface',
    'auth_base.html': 'autenticacao', 'login.html': 'autenticacao', 'cadastro.html': 'autenticacao',
    'esqueci_senha.html': 'autenticacao', 'redefinir_senha.html': 'autenticacao',
    'onboarding.html': 'onboarding-dashboard', '_onboarding_whatsapp_step.html': 'onboarding-dashboard',
    'dashboard.html': 'onboarding-dashboard', '_dashboard_summary.html': 'onboarding-dashboard',
    '_dashboard_whatsapp_card.html': 'onboarding-dashboard', '_dashboard_calendar_card.html': 'onboarding-dashboard',
    'conversas.html': 'whatsapp-conversas', '_chat_list.html': 'whatsapp-conversas', '_chat_view.html': 'whatsapp-conversas',
    '_chat_messages.html': 'whatsapp-conversas', '_chat_scheduled.html': 'whatsapp-conversas',
    '_scheduled_panel.html': 'whatsapp-conversas', '_scheduled_panel_list.html': 'whatsapp-conversas',
    'configuracoes.html': 'configuracoes-conexoes', '_connections.html': 'configuracoes-conexoes',
    '_preferences.html': 'configuracoes-conexoes', '_whatsapp_list.html': 'configuracoes-conexoes',
    '_whatsapp_picker_options.html': 'configuracoes-conexoes',
    'schedules.html': 'agendamentos', '_table.html': 'agendamentos', '_bulk_bar.html': 'agendamentos',
    '_schedule_form.html': 'agendamentos', '_schedule_fields.html': 'agendamentos',
    '_schedule_form_response.html': 'agendamentos', '_schedule_detail_modal.html': 'agendamentos',
    '_schedule_edit_modal.html': 'agendamentos',
    'calendario.html': 'calendario', 'calendario_dia.html': 'calendario', '_calendar_month_grid.html': 'calendario',
    '_calendar_day_view.html': 'calendario', '_calendar_event_modal.html': 'calendario',
    '_calendar_event_detail_modal.html': 'calendario', '_calendar_confirm_delete.html': 'calendario',
    '_calendar_automation_modal.html': 'calendario', '_calendar_automation_preview.html': 'calendario',
    '_similar_events_box.html': 'calendario', '_similar_events_checklist.html': 'calendario',
    '_contact_options.html': 'calendario',
    'planos.html': 'planos-faturamento', 'planos_upgrade.html': 'planos-faturamento',
    'planos_pagamento.html': 'planos-faturamento',
    'admin/': 'administracao',
}
# Testes: domínio da regra que o arquivo cobre (infraestrutura = testes).
TEST_FEATURES = {
    'test_admin.py': 'administracao', 'test_api.py': 'api', 'test_app_settings.py': 'arquitetura',
    'test_billing_plans.py': 'planos-faturamento', 'test_calendar_api.py': 'api',
    'test_calendar_providers.py': 'calendario', 'test_calendar_service.py': 'calendario',
    'test_calendar_sync.py': 'calendario', 'test_calendar_web.py': 'calendario', 'test_chats.py': 'whatsapp-conversas',
    'test_configuracoes.py': 'configuracoes-conexoes', 'test_logs_privacy.py': 'privacidade',
    'test_media_messages.py': 'agendamentos', 'test_migration_legacy_data.py': 'dados-migracoes',
    'test_migration_v14.py': 'dados-migracoes', 'test_multi_tenant_isolation.py': 'autenticacao',
    'test_multi_whatsapp_dispatch.py': 'agendamentos', 'test_onboarding.py': 'onboarding-dashboard',
    'test_privacy_crypto.py': 'privacidade', 'test_privacy_lifecycle.py': 'privacidade',
    'test_recipients.py': 'whatsapp-conversas', 'test_recurrence.py': 'agendamentos',
    'test_scheduled_panel.py': 'whatsapp-conversas', 'test_scheduler.py': 'agendamentos',
    'test_scheduling_service.py': 'agendamentos', 'test_scheduling_ui.py': 'agendamentos',
    'test_security_hardening.py': 'autenticacao', 'test_templates_csp.py': 'interface',
    'test_time_sync.py': 'arquitetura', 'test_timing.py': 'agendamentos', 'test_waha.py': 'whatsapp-conversas',
    'test_whatsapp_service.py': 'whatsapp-conversas',
}

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument('--rev', default='HEAD', help='commit, branch ou tag a inventariar (padrão: HEAD)')
parser.add_argument('--no-write', action='store_true', help='só imprime o resumo (útil para comparar revisões)')
args = parser.parse_args()
unmapped = []

def git(*cmd):
    return subprocess.run(['git', '-C', str(REPO), *cmd], check=True, capture_output=True).stdout

def by_prefix(table, path):
    hits = [k for k in table if path == k or (k.endswith('/') and path.startswith(k))]
    return table[max(hits, key=len)] if hits else None

def file_domain(path):
    d = by_prefix(FILE_DOMAINS, path)
    if d is None:
        unmapped.append('arquivo ' + path)
    return d

def template_feature(path):
    d = by_prefix(TEMPLATE_FEATURES, path[len(TPL):])
    if d is None:
        unmapped.append('template ' + path)
    return d

def test_feature(path):
    if not path.startswith('app/tests/test_'):
        return 'testes'
    d = TEST_FEATURES.get(path.rsplit('/', 1)[1])
    if d is None:
        unmapped.append('teste ' + path)
    return d

def sections(path, lines):
    """[(linha, domínio)] das seções de arquivos compartilhados."""
    table = SECTION_DOMAINS.get(path)
    if not table:
        return []
    out = []
    for i, line in enumerate(lines, 1):
        if not line.startswith('#'):
            continue
        title = line.strip('#').strip().strip('-').strip()
        if not title or set(title) <= set('-'):
            continue
        prev = lines[i - 2] if i >= 2 else ''
        boxed = prev.startswith('# ---') and set(prev.strip('# ')) <= set('-')
        if not (line.startswith('# ----') or boxed):
            continue
        keys = [k for k in table if title.startswith(k)]
        if keys:
            out.append((i, table[max(keys, key=len)]))
        elif line.startswith('# ----'):
            unmapped.append(f'seção "{title}" em {path}:{i}')
    return out

def symbol_domain(path, name, line, secs, default):
    top = name.split('.')[0]
    if (path, name) in SYMBOL_DOMAINS:
        return SYMBOL_DOMAINS[(path, name)]
    if (path, top) in SYMBOL_DOMAINS:
        return SYMBOL_DOMAINS[(path, top)]
    current = default
    for start, dom in secs:
        if start <= line:
            current = dom
    return current

SHA = git('rev-parse', '--verify', args.rev + '^{commit}').decode().strip()
manifest = {'files': []}
for line in git('ls-tree', '-r', '-l', '--full-tree', SHA).decode().splitlines():
    meta, path = line.split('\t', 1)
    mode, kind, blob, size = meta.split()
    if kind == 'blob':
        manifest['files'].append({'path': path, 'sha': blob, 'size': int(size)})

inventory = {'repository': REPOSITORY, 'commit': SHA,
             'method': 'Análise estática AST/texto dos blobs do Git, sem importar app nem executar testes.',
             'files': [], 'functions': [], 'classes': [], 'tables': [], 'routes': [], 'router_includes': [],
             'automatic_routes': [], 'templates': [], 'test_definitions': [], 'integrity_mismatches': []}

def expr(n):
    return ast.unparse(n) if n is not None else None

class Visitor(ast.NodeVisitor):
    def __init__(self, path, router_prefixes, router_dependencies, secs, default):
        self.path = path
        self.scope = []
        self.prefixes = router_prefixes
        self.dependencies = router_dependencies
        self.secs = secs
        self.default = default

    def visit_ClassDef(self, node):
        fields = [s.target.id for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
        name = '.'.join(self.scope + [node.name])
        record = {'file': self.path, 'line': node.lineno, 'name': name, 'bases': [expr(x) for x in node.bases],
            'fields': fields, 'keywords': {x.arg: expr(x.value) for x in node.keywords},
            'domain': symbol_domain(self.path, name, node.lineno, self.secs, self.default)}
        inventory['classes'].append(record)
        if record['keywords'].get('table') == 'True':
            tablename = next((s.value.value for s in node.body if isinstance(s, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == '__tablename__' for t in s.targets)
                              and isinstance(s.value, ast.Constant)), None)
            inventory['tables'].append({'table': tablename, 'model': name, 'file': self.path, 'line': node.lineno,
                                        'fields': fields, 'domain': record['domain']})
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self.function(node)

    def visit_AsyncFunctionDef(self, node):
        self.function(node)

    def function(self, node):
        test = self.path.startswith('app/tests/')
        name = '.'.join(self.scope + [node.name])
        record = {'file': self.path, 'line': node.lineno, 'end_line': node.end_lineno,
            'name': name, 'async': isinstance(node, ast.AsyncFunctionDef),
            'signature': expr(node.args), 'returns': expr(node.returns),
            'decorators': [expr(d) for d in node.decorator_list],
            'doc': (ast.get_docstring(node) or '').strip().split('\n\n')[0].replace('\n', ' ')[:200],
            'domain': symbol_domain(self.path, name, node.lineno, self.secs, self.default)}
        inventory['functions'].append(record)
        if test and node.name.startswith('test_'):
            params = [expr(d) for d in node.decorator_list if 'parametrize' in (expr(d) or '')]
            inventory['test_definitions'].append({**record, 'parametrized': bool(params)})
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
                    'router_dependencies': self.dependencies.get(router, []), 'options': kw,
                    'domain': record['domain']})
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

def lines_of(txt, pattern, group=0, flags=0):
    out = []
    for m in re.finditer(pattern, txt, flags):
        out.append({'line': txt.count('\n', 0, m.start()) + 1, 'value': m.group(group)})
    return out

def scan_template(path, txt):
    """HTMX e JavaScript por linha. Regex não interpreta JS: confira no arquivo."""
    hx = lines_of(txt, r'\b(hx-[\w:.-]+)=(?:"([^"]*)"|\'([^\']*)\')')
    for h, m in zip(hx, re.finditer(r'\b(hx-[\w:.-]+)=(?:"([^"]*)"|\'([^\']*)\')', txt)):
        h['value'] = {'attr': m.group(1), 'value': m.group(2) if m.group(2) is not None else m.group(3)}
    return {'file': path, 'feature_domain': template_feature(path), 'domain': 'interface',
        'extends_includes': re.findall(r'{%\s*(?:extends|include|import|from)\s+[\'\"]([^\'\"]+)', txt),
        'htmx_attributes': sorted(set(re.findall(r'(hx-[\w-]+)=[\'\"]([^\'\"]+)', txt))),
        'htmx': [{'line': h['line'], **h['value']} for h in hx],
        'script_tags': lines_of(txt, r'<script\b[^>]*>'),
        'named_js_functions': re.findall(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', txt),
        'js_functions': lines_of(txt, r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', 1),
        'js_assigned_functions': lines_of(txt, r'(?<![\w$.])((?:window\.)?[A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?(?:function\b|\([^()]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)', 1),
        'js_event_listeners': lines_of(txt, r'addEventListener\(\s*[\'"]([^\'"]+)[\'"]', 1),
        'htmx_js_hooks': lines_of(txt, r'\bhtmx\.(on|onLoad|ajax|process|trigger|find|swap)\b', 1),
        'inline_handlers': lines_of(txt, r'\s(on[a-z]+)=', 1),
        'timers': lines_of(txt, r'\b(setInterval|setTimeout|requestAnimationFrame)\s*\(', 1),
        'polling_triggers': lines_of(txt, r'hx-trigger=[\'"][^\'"]*\bevery\s+\d+m?s[^\'"]*[\'"]')}

for item in manifest['files']:
    path = item['path']
    raw = git('cat-file', 'blob', item['sha'])
    blob_sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob_sha != item['sha'] or len(raw) != item['size']:
        inventory['integrity_mismatches'].append(path)
    domain = file_domain(path)
    if path.startswith(TPL):
        domain = 'interface'
    frec = {'path': path, 'git_blob_sha': item['sha'], 'actual_blob_sha': blob_sha, 'bytes': len(raw), 'domain': domain}
    if path.startswith('app/tests/'):
        frec['feature_domain'] = test_feature(path)
    try:
        txt = raw.decode('utf-8')
    except UnicodeDecodeError:
        frec['binary'] = True
        inventory['files'].append(frec)
        continue
    frec['lines'] = len(txt.splitlines())
    # Só o código do app/testes; scripts de documentação ficam fora das contagens.
    if path.endswith('.py') and path.startswith('app/'):
        tree = ast.parse(txt, filename=path)
        prefixes = {}
        dependencies = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
                name = expr(n.value.func)
                if name in ('APIRouter', 'FastAPI'):
                    for target in n.targets:
                        if isinstance(target, ast.Name):
                            kws = {k.arg: k.value for k in n.value.keywords}
                            prefixes[target.id] = next((k.value.value for k in n.value.keywords if k.arg == 'prefix'), '')
                            dependencies[target.id] = [expr(k.value) for k in n.value.keywords if k.arg == 'dependencies']
                            if name == 'FastAPI':
                                # Rotas automáticas: padrões do FastAPI quando o kwarg não é passado.
                                for kwarg, default in (('openapi_url', '/openapi.json'), ('docs_url', '/docs'),
                                                       ('redoc_url', '/redoc'), ('swagger_ui_oauth2_redirect_url', '/docs/oauth2-redirect')):
                                    value = expr(kws[kwarg]) if kwarg in kws else repr(default)
                                    inventory['automatic_routes'].append({'file': path, 'line': n.lineno, 'kwarg': kwarg,
                                        'value': value, 'explicit': kwarg in kws})
            if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                    and n.value.func.attr == 'include_router'):
                inventory['router_includes'].append({'file': path, 'line': n.lineno,
                    'router': expr(n.value.args[0]) if n.value.args else None,
                    'keywords': {k.arg: expr(k.value) for k in n.value.keywords}})
        frec['imports'] = [expr(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        default = test_feature(path) if path.startswith('app/tests/') else domain
        Visitor(path, prefixes, dependencies, sections(path, txt.splitlines()), default).visit(tree)
    if path.endswith('.html') and path.startswith(TPL):
        inventory['templates'].append(scan_template(path, txt))
    inventory['files'].append(frec)

if unmapped:
    sys.exit('Sem domínio (atualize as tabelas de build_inventory.py):\n  ' + '\n  '.join(unmapped))
prefixed = [x for x in inventory['router_includes'] if 'prefix' in x['keywords']]
if prefixed:
    sys.exit('include_router com prefix não suportado pelo cálculo de caminhos: ' + repr(prefixed))

app_functions = [x for x in inventory['functions'] if not x['file'].startswith('app/tests/')]
inventory['summary'] = {
    'tracked_files': len(inventory['files']),
    'tracked_files_outside_documentation': sum(x['domain'] != META for x in inventory['files']),
    'application_python_files': sum(x['path'].startswith(APP) and x['path'].endswith('.py') for x in inventory['files']),
    'python_functions_and_methods': len(app_functions),
    'application_classes': sum(not x['file'].startswith('app/tests/') for x in inventory['classes']),
    'declared_http_routes': len(inventory['routes']),
    'rest_routes_under_api': sum(x['path'].startswith('/api/') for x in inventory['routes']),
    'automatic_fastapi_routes_enabled': sum(x['value'] != 'None' for x in inventory['automatic_routes']),
    'templates': len(inventory['templates']),
    'named_inline_js_functions': sum(len(x['named_js_functions']) for x in inventory['templates']),
    'js_event_listeners': sum(len(x['js_event_listeners']) for x in inventory['templates']),
    'inline_event_handler_attributes': sum(len(x['inline_handlers']) for x in inventory['templates']),
    'test_files': sum(x['path'].startswith('app/tests/test_') for x in inventory['files']),
    'test_function_definitions': len(inventory['test_definitions']),
    'parametrized_test_definitions': sum(x['parametrized'] for x in inventory['test_definitions']),
    'sqlmodel_tables': len(inventory['tables']),
    'integrity_mismatches': len(inventory['integrity_mismatches'])}
print(json.dumps(inventory['summary'], ensure_ascii=False, indent=2))
if inventory['integrity_mismatches']:
    print('Divergências de cópia: ' + repr(inventory['integrity_mismatches']))
print('Rotas por arquivo: ' + repr(dict(collections.Counter(x['file'] for x in inventory['routes']))))
if args.no_write:
    sys.exit(0)

(BASE / 'INVENTARIO.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
# Links relativos (a partir de docs/about/): funcionam no GitHub e localmente,
# inclusive quando a revisão inventariada ainda não foi enviada ao GitHub. As
# linhas valem para o commit abaixo; depois de mudar o código, gere de novo.
rows = ['# Rotas HTTP declaradas no código', '', f'Base: `{SHA}`.', '',
    'Extração estática dos decoradores e prefixos APIRouter. Inclui páginas, parciais HTMX, REST e webhook; exclui rotas automáticas do FastAPI (listadas ao final). Não representa chamadas executadas nem validação funcional.', '',
    'Gerado por `build_inventory.py`; não edite à mão. O contrato de cada rota está no about.md do domínio.', '',
    '| Método | Caminho | Handler | Domínio | Fonte |', '|---|---|---|---|---|']
for r in inventory['routes']:
    link = f'../../{r["file"]}#L{r["line"]}'
    rows.append(f'| {r["method"]} | `{r["path"]}` | `{r["handler"]}` | [{r["domain"]}]({r["domain"]}/about.md) | [código]({link}) |')
rows += ['', '## Rotas automáticas do FastAPI', '',
         'Derivadas dos argumentos de `FastAPI(...)`: argumento ausente = padrão do FastAPI. Não verificado em execução; middlewares podem alterar o acesso.', '',
         '| Argumento | Valor efetivo | Explícito | Fonte |', '|---|---|---|---|']
for a in inventory['automatic_routes']:
    rows.append(f'| `{a["kwarg"]}` | `{a["value"]}` | {"sim" if a["explicit"] else "não (padrão)"} | [código](../../{a["file"]}#L{a["line"]}) |')
(BASE / 'ROTAS.md').write_text('\n'.join(rows) + '\n')

# Anexo por domínio: tudo o que o inventário associa ao domínio.
def esc(s):
    return (s or '').replace('|', '\\|').replace('\n', ' ')

for slug, title in DOMAINS.items():
    up = '../../../'
    out = [f'# {title} — inventário (anexo gerado)', '',
           f'Base: `{SHA}`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. '
           'Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).', '']
    files = [f for f in inventory['files'] if f['domain'] == slug]
    if files:
        out += ['## Arquivos', '', '| Arquivo | Linhas |', '|---|---|']
        out += [f'| [`{f["path"]}`]({up}{f["path"]}) | {f.get("lines", "binário")} |' for f in files]
        out += ['']
    shared = sorted({f['file'] for f in inventory['functions'] if f['domain'] == slug}
                    - {f['path'] for f in files})
    if shared:
        out += ['Símbolos deste domínio em arquivos de outro domínio: ' + ', '.join(f'[`{p}`]({up}{p})' for p in shared) + '.', '']
    routes = [r for r in inventory['routes'] if r['domain'] == slug]
    if routes:
        out += ['## Rotas', '', '| Método | Caminho | Handler | Fonte |', '|---|---|---|---|']
        out += [f'| {r["method"]} | `{r["path"]}` | `{r["handler"]}` | [{r["file"].rsplit("/", 1)[1]}:{r["line"]}]({up}{r["file"]}#L{r["line"]}) |' for r in routes]
        out += ['']
    tables = [t for t in inventory['tables'] if t['domain'] == slug]
    if tables:
        out += ['## Tabelas SQLModel', '', '| Tabela | Modelo | Campos | Fonte |', '|---|---|---|---|']
        out += [f'| `{t["table"]}` | `{t["model"]}` | {len(t["fields"])} | [models.py:{t["line"]}]({up}{t["file"]}#L{t["line"]}) |' for t in tables]
        out += ['']
    classes = [c for c in inventory['classes'] if c['domain'] == slug and not c['file'].startswith('app/tests/')]
    if classes:
        out += ['## Classes', '', '| Classe | Bases | Fonte |', '|---|---|---|']
        out += [f'| `{c["name"]}` | {esc(", ".join(c["bases"]))} | [{c["file"].rsplit("/", 1)[1]}:{c["line"]}]({up}{c["file"]}#L{c["line"]}) |' for c in classes]
        out += ['']
    funcs = [f for f in inventory['functions'] if f['domain'] == slug and not f['file'].startswith('app/tests/')]
    if funcs:
        route_handlers = {(r['file'], r['handler']) for r in inventory['routes']}
        out += ['## Funções e métodos', '', 'Docstring = primeira frase do código (não verificada).', '',
                '| Símbolo | Tipo | Fonte | Docstring |', '|---|---|---|---|']
        for f in funcs:
            kind = ', '.join(k for k, on in (('rota', (f['file'], f['name']) in route_handlers), ('async', f['async']),
                                              ('aninhada', '.' in f['name'] and f['name'].split('.')[0][:1].islower())) if on)
            out.append(f'| `{f["name"]}` | {kind} | [{f["file"].rsplit("/", 1)[1]}:{f["line"]}]({up}{f["file"]}#L{f["line"]}) | {esc(f["doc"][:120])} |')
        out += ['']
    tpls = [t for t in inventory['templates'] if t['feature_domain'] == slug]
    if tpls:
        out += ['## Templates desta funcionalidade', '', 'Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).', '',
                '| Template | hx-* | Listeners JS | Handlers inline | Polling |', '|---|---|---|---|---|']
        out += [f'| [`{t["file"][len(TPL):]}`]({up}{t["file"]}) | {len(t["htmx"])} | {len(t["js_event_listeners"])} | {len(t["inline_handlers"])} | {len(t["polling_triggers"])} |' for t in tpls]
        out += ['']
    if slug == 'interface':
        out += ['## Catálogo HTMX/JavaScript por template', '',
                'Extração por regex (não interpreta JS). Linhas na revisão-base.', '']
        for t in inventory['templates']:
            items = []
            for label, key in (('funções', 'js_functions'), ('funções atribuídas', 'js_assigned_functions'),
                               ('addEventListener', 'js_event_listeners'), ('htmx.*', 'htmx_js_hooks'),
                               ('handlers inline', 'inline_handlers'), ('timers', 'timers'), ('polling', 'polling_triggers')):
                vals = t[key]
                if vals:
                    shown = ', '.join(f'`{esc(str(v["value"]))[:60]}`:{v["line"]}' for v in vals[:40])
                    more = f' (+{len(vals) - 40})' if len(vals) > 40 else ''
                    items.append(f'- {label} ({len(vals)}): {shown}{more}')
            reqs = [h for h in t['htmx'] if h['attr'] in ('hx-get', 'hx-post', 'hx-put', 'hx-delete', 'hx-patch')]
            if reqs:
                items.append(f'- requisições hx ({len(reqs)}): ' + ', '.join(f'`{h["attr"][3:].upper()} {esc(h["value"])[:70]}`:{h["line"]}' for h in reqs))
            if items:
                out += [f'### [`{t["file"][len(TPL):]}`]({up}{t["file"]}) — {t["feature_domain"]}', ''] + items + ['']
    tests = [t for t in inventory['test_definitions'] if t['domain'] == slug]
    if tests:
        out += ['## Testes (definições, não execuções)', '',
                'Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.', '']
        for path, group in collections.OrderedDict((p, [t for t in tests if t['file'] == p]) for p in dict.fromkeys(t['file'] for t in tests)).items():
            par = sum(t['parametrized'] for t in group)
            out.append(f'- [`{path}`]({up}{path}) — {len(group)} funções' + (f' ({par} parametrizadas)' if par else '') + ': '
                       + ', '.join(f'`{t["name"]}`' for t in group))
        out += ['']
    if slug == 'testes':
        helpers = [f for f in inventory['functions'] if f['file'].startswith('app/tests/') and not f['name'].split('.')[-1].startswith('test_')]
        out += ['## Funções auxiliares e fixtures dos testes', '', '| Símbolo | Fonte |', '|---|---|']
        out += [f'| `{f["name"]}` | [{f["file"].rsplit("/", 1)[1]}:{f["line"]}]({up}{f["file"]}#L{f["line"]}) |' for f in helpers]
        out += ['']
    (BASE / slug).mkdir(exist_ok=True)
    (BASE / slug / 'INVENTARIO.md').write_text('\n'.join(out))

if git('status', '--porcelain', '--', 'app').strip():
    print('Aviso: há alterações locais em app/ que NÃO entram neste inventário (ele lê o commit ' + SHA[:7] + ').')
