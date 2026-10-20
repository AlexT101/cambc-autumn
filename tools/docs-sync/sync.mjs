// Mirror the Cambridge Battlecode online docs (handbook, guides, champion pages,
// API reference, patch notes and images) into docs/ as Markdown.
//
// The site is a JS single-page app: all content lives as data inside its JS
// bundles, which are served behind CloudFront signed cookies set by the HTML
// page. We fetch the bundles with those cookies, parse them with acorn and read
// the data through a small side-effect-free interpreter (evaljs.mjs) - none of
// the downloaded code is executed.
//
// Usage: (cd tools/docs-sync && npm install && node sync.mjs)

import { mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, posix, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadModule, unsupportedLog } from './evaljs.mjs';

const SITE = 'https://2026a.battlecode.co.uk';
const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT = join(REPO, 'docs');
const LANGS = ['cpp', 'rust', 'python', 'ocaml'];
const FENCE = { cpp: 'cpp', rust: 'rust', python: 'python', ocaml: 'ocaml' };

// ---------------------------------------------------------------- fetching

let cookie = '';
async function refreshCookies() {
  const res = await fetch(`${SITE}/game/docs`);
  if (!res.ok) throw new Error(`GET /game/docs: ${res.status}`);
  cookie = res.headers.getSetCookie().map(c => c.split(';')[0]).join('; ');
  return res.text();
}
async function get(path, binary = false) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const res = await fetch(SITE + path, { headers: { cookie } });
    if (res.ok) return binary ? Buffer.from(await res.arrayBuffer()) : res.text();
    if (res.status === 403 && attempt === 0) { await refreshCookies(); continue; } // cookies last 5 minutes
    throw new Error(`GET ${path}: ${res.status}`);
  }
}

const work = join(tmpdir(), 'cambc-docs-sync');
rmSync(work, { recursive: true, force: true });
mkdirSync(work, { recursive: true });

const html = await refreshCookies();
const entry = html.match(/\/service\/assets\/(service-[\w-]+\.js)/)?.[1];
if (!entry) throw new Error('Could not find the service entry bundle in /game/docs');
const entrySrc = await get(`/service/assets/${entry}`);
writeFileSync(join(work, entry), entrySrc);
const chunkName = (prefix) => {
  const m = entrySrc.match(new RegExp(`assets/(${prefix}-[\\w-]{8}(?:-\\w+)?\\.js)`));
  if (!m) throw new Error(`Could not find the ${prefix} chunk`);
  return m[1];
};
const chunks = { docs: chunkName('docs'), grid: chunkName('ChampionGrid') };
// Fetch each chunk plus the chunks it statically imports, so cross-chunk data resolves.
const fetched = new Set([entry]);
async function fetchChunk(name) {
  if (fetched.has(name)) return;
  fetched.add(name);
  const src = await get(`/service/assets/${name}`);
  writeFileSync(join(work, name), src);
  for (const [, dep] of src.matchAll(/from"\.\/([\w-]+\.js)"/g)) await fetchChunk(dep);
}
for (const name of Object.values(chunks)) await fetchChunk(name);
console.log('chunks:', chunks);

const docs = loadModule(join(work, chunks.docs));
const grid = loadModule(join(work, chunks.grid));

// ---------------------------------------------------------------- data

// Minified names change with every site build, so find them through the site's own code:
// the Agents.md download buttons, the sidebar and the visual block renderer.
const nameIn = (re, what) => {
  const m = docs.src.match(re);
  if (!m) throw new Error(`Could not find ${what} in the docs chunk`);
  return m.slice(1);
};
const [rulesExportName, articlesName] = nameIn(/generate:\(\)=>([\w$]+)\(\[\.\.\.[\w$]+\.map\([\w$]+=>([\w$]+)\.find/, 'the GameRules.md generator');
const [apiExportName, langLabelName, apiEntriesName] = nameIn(/generate:\(\)=>([\w$]+)\([\w$]+,([\w$]+)\[[\w$]+\],([\w$]+)\[[\w$]+\]\)/, 'the BotAPI*.md generator');
const [groupsName] = nameIn(/([\w$]+)\.find\([\w$]+=>[\w$]+\.title===`Game rules`\)/, 'the sidebar groups');
const [visualTextName] = nameIn(/case`visual`:\{let [\w$]+=([\w$]+)\[[\w$]+\.name\]/, 'the diagram descriptions');

const groups = docs.get(groupsName);           // sidebar groups: [{title, ids}]
const baseArticles = docs.get(articlesName);   // all articles, guides evaluated for C++
const visualText = docs.get(visualTextName);   // Markdown descriptions of rule diagrams
const apiEntries = docs.get(apiEntriesName);   // {lang: [{group,name,signature,description,example}]}
const langLabel = docs.get(langLabelName);     // {cpp: 'C++', ...}
const gridDecl = (test, what) => {
  for (const [name, node] of grid.decls) if (node && test(node, grid.src.slice(node.start, node.end))) return grid.get(name);
  throw new Error(`Could not find ${what} in the ChampionGrid chunk`);
};
const champions = gridDecl((n, s) => n.type === 'ArrayExpression' && s.includes('bodies:') && s.includes('sharedPassive'), 'the champion designs');
const championArt = gridDecl((n, s) => n.type === 'FunctionDeclaration' && s.includes('banner:') && s.includes('thumb:'), 'the champion art lookup');
const rulesExport = docs.get(rulesExportName); // the site's own "GameRules.md" generator
const apiExport = docs.get(apiExportName);     // the site's own "BotAPI*.md" generator
console.log('names:', { groupsName, articlesName, visualTextName, apiEntriesName, langLabelName, rulesExportName, apiExportName });

const articleOf = new Map(baseArticles.map(a => [a.id, a]));
const ruleIds = groups.find(g => g.title === 'Game rules').ids;
const guideIds = groups.find(g => g.title === 'Guides').ids;
// Language-dependent articles are built by functions taking a language key;
// the article list calls them as e.g. he(`cpp`).
const guideBuilders = {};
{
  const list = docs.decls.get(articlesName);
  for (const [, fn] of docs.src.slice(list.start, list.end).matchAll(/([\w$]+)\(`cpp`\)/g)) {
    const build = docs.get(fn);
    if (typeof build === 'function') guideBuilders[build('cpp').id] = build;
  }
}
const articleFor = (id, lang) => guideBuilders[id] ? guideBuilders[id](lang) : articleOf.get(id);

// ---------------------------------------------------------------- paths & links

const pathOf = (id, lang = 'cpp') => {
  const i = ruleIds.indexOf(id);
  if (i >= 0) return `handbook/${String(i + 1).padStart(2, '0')}-${id}.md`;
  if (id === 'glossary') return 'handbook/glossary.md';
  if (id === 'champions') return 'champions/README.md';
  if (articleOf.get(id)?.group === 'Champions') return `champions/${id}.md`;
  if (guideIds.includes(id)) return `guides/${lang}/${id}.md`;
  if (id === 'bot-api') return `api/${lang}.md`;
  if (id === 'agents') return 'llm/README.md';
  if (id === 'welcome') return 'README.md';
  return null;
};
const rel = (from, to) => {
  const r = posix.relative(posix.dirname(from), to);
  return r.startsWith('.') ? r : `./${r}`;
};
function resolveHref(href, from, lang) {
  if (href.startsWith('/game/docs')) {
    const [p, hash] = href.slice('/game/docs'.length).replace(/^\//, '').split('#');
    const id = p === '' ? 'welcome' : p === 'turn-order' ? 'your-first-turn' : p;
    const target = pathOf(id, lang);
    if (target) return rel(from, target) + (hash ? `#${hash}` : '');
  }
  if (href === '/game/api') return rel(from, `api/${lang}.md`);
  if (href.startsWith('/')) return SITE + href;
  return href;
}

// ---------------------------------------------------------------- images

const images = new Map(); // site path -> local file name
function image(sitePath, name) {
  if (!sitePath || typeof sitePath !== 'string' || !sitePath.startsWith('/service/assets/')) return null;
  if (!images.has(sitePath)) {
    const file = sitePath.split('/').pop().replace(/-[\w-]{8}(\.\w+)$/, '$1');
    images.set(sitePath, name ? name + file.slice(file.lastIndexOf('.')) : file);
  }
  return `images/${images.get(sitePath)}`;
}

// ---------------------------------------------------------------- diagram text

// Interactive diagrams are React components. We collect their visible text
// (labels, step titles, captions) from the AST in source order, following
// referenced data arrays and child components, and skipping class names,
// styles, tag names and comparison keys.
const SKIP_KEYS = new Set(['className', 'key', 'style', 'role', 'as', 'type', 'id', 'href', 'src', 'to', 'viewBox', 'd',
  'fill', 'stroke', 'transform', 'xmlns', 'variant', '$variant', 'tone', 'icon', 'kind', 'color', 'size', 'align',
  'position', 'width', 'height', 'x', 'y', 'cx', 'cy', 'r', 'points', 'loading', 'name', 'data-state', 'aria-hidden',
  'tabIndex', 'htmlFor', 'value', 'pace', 'shape', 'side', 'team', 'tile', 'state', 'mode', 'anchor', 'dir']);
function componentText(mod, fnName, seen = new Set()) {
  const out = [];
  const visit = (node, parent, parentKey) => {
    if (!node || typeof node.type !== 'string') return;
    if (node.type === 'Property' && !node.computed) {
      const k = node.key.name ?? node.key.value;
      if (SKIP_KEYS.has(k) || /^on[A-Z]/.test(k)) return;
      visit(node.value, node, 'value');
      return;
    }
    if (node.type === 'BinaryExpression' && /^[!=]==?$/.test(node.operator)) return;
    if (node.type === 'SwitchCase') { node.consequent.forEach(c => visit(c, node)); return; }
    if (node.type === 'MemberExpression' && node.computed && node.property.type !== 'Identifier') { visit(node.object, node); return; }
    if (node.type === 'CallExpression') {
      const callee = node.callee.type === 'SequenceExpression' ? node.callee.expressions.at(-1) : node.callee;
      const isJsx = callee.type === 'MemberExpression' && /^jsxs?$/.test(callee.property.name);
      if (isJsx) {
        const [tag, ...rest] = node.arguments;
        if (tag?.type === 'Identifier') follow(tag.name);
        rest.forEach(a => visit(a, node));
        return;
      }
      if (callee.type === 'MemberExpression' && /^(useState|useMemo|useRef|useEffect|replace|split|join|test|match)$/.test(callee.property.name)) {
        if (callee.property.name === 'join' || callee.property.name === 'replace') visit(callee.object, node);
        return;
      }
    }
    if (node.type === 'Literal' && typeof node.value === 'string') { keep(node.value); return; }
    if (node.type === 'TemplateLiteral') {
      keep(node.quasis.map(q => q.value.cooked).join('N'));
      node.expressions.forEach(e => visit(e, node));
      return;
    }
    if (node.type === 'Identifier' && parentKey !== 'property' && parentKey !== 'key') { follow(node.name); return; }
    for (const [k, v] of Object.entries(node)) {
      if (k === 'type' || k === 'start' || k === 'end') continue;
      if (Array.isArray(v)) v.forEach(c => visit(c, node, k));
      else if (v && typeof v.type === 'string') visit(v, node, k);
    }
  };
  const follow = (name) => {
    if (name.length < 2 && !/^[A-Z$]/.test(name)) return;   // minified locals are single lowercase letters
    if (seen.has(name) || !mod.decls.has(name)) return;
    const decl = mod.decls.get(name);
    if (!decl) return;
    const isData = decl.type === 'ArrayExpression' || decl.type === 'ObjectExpression';
    const isComponent = decl.type === 'FunctionDeclaration';
    if (!isData && !isComponent) return;
    seen.add(name);
    visit(isComponent ? decl.body : decl, null);
  };
  const keep = (raw) => {
    const s = raw.replace(/\[\[icon:[\w:-]+\]\]/g, '').replace(/\s+/g, ' ').trim();
    if (!/[A-Za-z]/.test(s) || s.length < 2) return;
    if (/^[a-z0-9_$-]+$/.test(s) && !/^[a-z]+ [a-z]/.test(s)) return;      // ids / single lowercase tokens
    if (/^[a-z0-9_ -]+$/.test(s) && s.includes('-')) return;                // class names
    if (/[;{}<>]|:\s*\d|\bpx\b|#[0-9a-f]{3,8}\b|rgba?\(|var\(--|^\/|\.(png|webp|svg|js)$|^https?:/i.test(s)) return;
    if (/^(true|false|null|undefined|button|polite|assertive|presentation|img|group|list|listitem|region)$/i.test(s)) return;
    out.push(s);
  };
  seen.add(fnName);
  visit(mod.decls.get(fnName).body, null);
  return [...new Set(out)];
}
const visualComponents = (() => {
  const m = docs.src.match(/function [\w$]+\(\{name:e\}\)\{let t=(\{[^}]+\})\[e\]/);
  if (!m) return {};
  return Object.fromEntries([...m[1].matchAll(/"?([\w-]+)"?:([\w$]+)/g)].map(x => [x[1], x[2]]));
})();
const demoComponents = (() => {
  const out = {};
  for (const [, kind, comp] of docs.src.matchAll(/case`(bitboard-demo|bitboard-layout|distance-demo)`:return\(0,[\w$]+\.jsx\)\(([\w$]+)/g)) out[kind] = comp;
  return out;
})();
function diagramDetails(lines, summary) {
  if (!lines.length) return '';
  return `<details>\n<summary>${summary}</summary>\n\n${lines.map(l => `- ${l}`).join('\n')}\n\n</details>`;
}

// ---------------------------------------------------------------- rendering

const stripIcons = (s) => String(s).replace(/\[\[icon:[\w:-]+\]\]/gi, '').replace(/[ \t]+(?=[,.;:!?])/g, '').trim();
const cell = (s) => stripIcons(s).replace(/\|/g, '\\|').replace(/\r?\n/g, '<br>');
const table = (headings, rows) =>
  [headings, headings.map(() => '---'), ...rows].map(r => `| ${r.map(cell).join(' | ')} |`).join('\n');
const fence = (code, lang = '') => {
  const ticks = '`'.repeat(Math.max(3, ...[...code.matchAll(/`+/g)].map(m => m[0].length + 1)));
  return `${ticks}${lang}\n${code}\n${ticks}`;
};
const stats = (body) => table(['Stat', 'Base', 'Growth per matching shard'],
  [['Health', body.stats[0], body.stats[1]], ['Strength', body.stats[2], body.stats[3]], ['Focus', body.stats[4], body.stats[5]]].map(r => r.map(String)))
  + `\n\nAttack type: ${body.attack}. Basic attack range: ${body.attack === 'Melee' ? 1 : 3} tiles.`;

function block(b, ctx, depth) {
  const h = (t) => `${'#'.repeat(Math.min(6, depth))} ${stripIcons(t)}`;
  switch (b.kind) {
    case 'text': return stripIcons(b.text);
    case 'subheading': return h(b.text);
    case 'image': { const p = image(b.src); return p ? `![${b.alt}](${rel(ctx.file, p)})` : `*Illustration: ${b.alt}*`; }
    case 'note': return `> **${stripIcons(b.title)}**\n>\n> ${stripIcons(b.text).replace(/\n/g, '\n> ')}`;
    case 'list': return b.items.map((t, i) => `${b.ordered ? `${i + 1}.` : '-'} ${stripIcons(t)}`).join('\n');
    case 'cards': return b.items.map(c => `- **${stripIcons(c.title)}**${c.text ? `: ${stripIcons(c.text)}` : ''}`).join('\n');
    case 'table': {
      let rows = b.rows;
      if (b.rowImages) rows = rows.map(r => {
        const p = image(b.rowImages[r[0]]);
        return p ? [`![${r[0]}](${rel(ctx.file, p)}) ${r[0]}`, ...r.slice(1)] : r;
      });
      return [b.caption ? `**${stripIcons(b.caption)}**` : '', table(b.headings, rows)].filter(Boolean).join('\n\n');
    }
    case 'details': return [h(b.title), ...b.blocks.map(x => block(x, ctx, depth + 1))].filter(Boolean).join('\n\n');
    case 'code': return [b.label ? `**${stripIcons(b.label)}**` : '', fence(b.code, b.language ?? '')].filter(Boolean).join('\n\n');
    case 'external-link': return `[${stripIcons(b.label)}](${resolveHref(b.href, ctx.file, ctx.lang)})`;
    case 'links': return b.ids.map(id => {
      const a = articleFor(id, ctx.lang), p = pathOf(id, ctx.lang);
      return a && p ? `- [${a.title}](${rel(ctx.file, p)})${a.summary ? ` — ${stripIcons(a.summary)}` : ''}` : `- ${id}`;
    }).join('\n');
    case 'visual': {
      const desc = visualText[b.name] ?? '';
      const comp = visualComponents[b.name];
      const lines = comp ? componentText(docs, comp).filter(l => !desc.includes(l)) : [];
      return [`> **Diagram: ${b.name}.** ${desc}`, diagramDetails(lines, 'Interactive diagram text')].filter(Boolean).join('\n\n');
    }
    case 'bitboard-demo': case 'bitboard-layout': case 'distance-demo': {
      const comp = demoComponents[b.kind];
      const lines = comp ? componentText(docs, comp) : [];
      return [`> *Interactive ${b.kind.replace('-', ' ')} on the website (${SITE}/game/docs).*`,
        diagramDetails(lines, 'Demo text')].filter(Boolean).join('\n\n');
    }
    case 'kit': return [`**${b.body.name}**`, b.body.passive ? `**Passive:** ${b.body.passive}` : '',
      ...b.body.abilities.map((a, i) => `${h(`Slot ${i}: ${a.name}`)}\n\n${a.effect}\n\n- **Target / range:** ${a.target}\n- **Walking:** ${a.walking}\n- **Cooldown:** 8 owner turn ends`)]
      .filter(Boolean).join('\n\n');
    case 'stats': return stats(b.body);
    case 'roster': return table(['Champion', 'Bodies', 'Tags', 'Summary'], champions.map(c => [
      `[${c.name}](${rel(ctx.file, pathOf(c.id))})`, c.bodies.map(x => `${x.name} (${x.attack.toLowerCase()})`).join(', '), c.tags.join(', '), c.summary]));
    case 'compare': return table(['Champion', 'Attack', 'Health', '+/shard', 'Strength', '+/shard', 'Focus', '+/shard'],
      champions.flatMap(c => c.bodies.map(x => [x.name, x.attack, ...x.stats.map(String)])));
    case 'api-reference': return `See the full [${langLabel[ctx.lang]} API reference](${rel(ctx.file, `api/${ctx.lang}.md`)}).`;
    case 'agent-downloads': return `The generated files are in [llm/](${rel(ctx.file, 'llm/README.md')}).`;
    default: return `> *(Unrendered block kind: ${b.kind})*`;
  }
}

function articleMarkdown(a, file, lang = 'cpp', { headerExtra = '' } = {}) {
  const ctx = { file, lang };
  const parts = [`# ${a.title}`];
  if (a.summary) parts.push(`*${stripIcons(a.summary)}*`);
  if (headerExtra) parts.push(headerExtra);
  for (const s of a.sections) {
    const body = s.blocks.map(b => block(b, ctx, 3)).filter(Boolean).join('\n\n');
    parts.push(s.title ? `## ${s.title}\n\n${body}` : body);
  }
  const related = (a.related ?? []).map(id => [articleFor(id, lang), pathOf(id, lang)]).filter(([x, p]) => x && p);
  if (related.length) parts.push(`---\n\n**See also:** ${related.map(([x, p]) => `[${x.title}](${rel(file, p)})`).join(' · ')}`);
  if (a.sources?.length) parts.push(`<sub>Engine sources cited by the handbook: ${a.sources.map(s => s.includes('`') ? s : `\`${s}\``).join(', ')}</sub>`);
  return parts.join('\n\n') + '\n';
}

// ---------------------------------------------------------------- API reference

function splitParams(desc) {
  const [main, ...params] = desc.split(/\s*@param\s+/);
  return { main: main.trim(), params: params.map(p => { const m = p.match(/^(\S+)\s*(.*)$/s); return { name: m[1], text: m[2].trim() }; }) };
}
function apiMarkdown(lang) {
  const file = `api/${lang}.md`;
  const entries = apiEntries[lang];
  const contextCount = new Map();
  for (const e of entries) contextCount.set(e.example?.context, (contextCount.get(e.example?.context) ?? 0) + 1);
  const groupsInOrder = [...new Set(entries.map(e => e.group))];
  const slug = (g) => g.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  // The site's bot-api article is only a search wrapper around this reference, so render its header only.
  const overview = articleFor('bot-api', lang);
  const others = LANGS.filter(l => l !== lang).map(l => `[${langLabel[l]}](./${l}.md)`).join(' · ');
  const parts = [`# ${overview.title}: ${langLabel[lang]}`, `*${overview.summary}*`,
    `Start with [Getting Started](${rel(file, pathOf('first-bot', lang))}). Other languages: ${others}.`,
    '## Contents', groupsInOrder.map(g => `- [${g}](#${slug(g)}) (${entries.filter(e => e.group === g).length})`).join('\n')];
  for (const g of groupsInOrder) {
    parts.push(`<a id="${slug(g)}"></a>\n\n## ${g}`);
    for (const e of entries.filter(x => x.group === g)) {
      const { main, params } = splitParams(e.description ?? '');
      const lines = [`### ${e.name}`, fence(e.signature, FENCE[lang])];
      if (main) lines.push(main);
      if (params.length) lines.push(params.map(p => `- \`${p.name}\`: ${p.text}`).join('\n'));
      // Most examples are auto-generated one-liners sharing a boilerplate context; keep only hand-written ones.
      const ex = e.example;
      if (ex?.code && contextCount.get(ex.context) <= 3) {
        lines.push(`*Example: ${ex.context}*`, fence(ex.code, FENCE[lang]));
        if (ex.note) lines.push(ex.note);
      }
      parts.push(lines.join('\n\n'));
    }
  }
  return [file, parts.join('\n\n') + '\n'];
}

// ---------------------------------------------------------------- patch notes

// Patch notes are served by the site's public API as Markdown with stat icon markup:
// `<:health[Health]:>` is a labelled icon, `<:health:>` a bare one.
const patchImages = new Map(); // local file name -> bytes
async function patchNotesMarkdown() {
  const patches = [];
  for (let cursor; ;) {
    const page = JSON.parse(await get(`/api/v1/patch-notes?limit=20${cursor ? `&after=${encodeURIComponent(cursor)}` : ''}`));
    patches.push(...page.items);
    if (!(cursor = page.nextCursor)) break;
  }
  const parts = ['# Patch notes', '*Balance changes to champions and the game, newest first.*'];
  if (!patches.length) parts.push(`No patches have been published yet (checked ${new Date().toISOString().slice(0, 10)}).`);
  for (const p of patches) {
    let body = p.bodyMarkdown.replace(/\r\n/g, '\n')
      .replace(/\s*\(\+?<:\w+:>\)/g, '')
      .replace(/<:\w+\[([^\]]*)\]:?>/g, '$1')
      .replace(/<:\w+:>/g, '')
      .replace(/ +:/g, ':')
      .replace(/^(#+) /gm, '##$1 ');
    for (const [, alt, path, id] of body.matchAll(/!\[([^\]]*)\]\((\/api\/v1\/patch-notes\/assets\/([\w-]+))\)/g)) {
      const res = await fetch(SITE + path, { headers: { cookie } });
      if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
      const ext = { 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif' }[res.headers.get('content-type')] ?? 'png';
      const file = `patch-${id.slice(0, 8)}.${ext}`;
      patchImages.set(file, Buffer.from(await res.arrayBuffer()));
      body = body.replace(path, `./images/${file}`);
    }
    parts.push(`## ${p.title} (${p.publishedAt.slice(0, 10)})`, body.trim());
  }
  return parts.join('\n\n') + '\n';
}

// ---------------------------------------------------------------- write

const files = new Map();
const add = (path, text) => files.set(path, text);

ruleIds.forEach(id => add(pathOf(id), articleMarkdown(articleOf.get(id), pathOf(id))));
add('handbook/glossary.md', articleMarkdown(articleOf.get('glossary'), 'handbook/glossary.md'));
add('champions/README.md', articleMarkdown(articleOf.get('champions'), 'champions/README.md'));
for (const a of baseArticles.filter(a => a.group === 'Champions' && a.id !== 'champions')) {
  const file = pathOf(a.id);
  const art = championArt(a.id);
  const p = image(art?.image, `champion-${a.id}`);
  add(file, articleMarkdown(a, file, 'cpp', { headerExtra: p ? `<img src="${rel(file, p)}" alt="${a.title}" width="320">` : '' }));
}
for (const lang of LANGS) {
  for (const id of guideIds) add(pathOf(id, lang), articleMarkdown(articleFor(id, lang), pathOf(id, lang), lang));
  const [file, text] = apiMarkdown(lang);
  add(file, text);
}
add('patch-notes.md', await patchNotesMarkdown());

// The site's own LLM exports, generated by its own (pure) generator functions.
const llmFiles = { 'GameRules.md': rulesExport([...ruleIds.map(id => articleOf.get(id)), ...baseArticles.filter(a => a.group === 'Champions')]) };
for (const lang of LANGS) llmFiles[`BotAPI${{ cpp: 'Cpp', rust: 'Rust', python: 'Python', ocaml: 'OCaml' }[lang]}.md`] = apiExport(lang, langLabel[lang], apiEntries[lang]);
for (const [name, text] of Object.entries(llmFiles)) add(`llm/${name}`, text);
add('llm/README.md', `# LLM exports\n\nThe single-file Markdown references the website offers under **Reference → Agents.md** ("Download markdown files for use with LLMs"), regenerated with the site's own generator.\n\n${Object.keys(llmFiles).map(f => `- [${f}](./${f})`).join('\n')}\n`);

const date = new Date().toISOString().slice(0, 10);
const link = (id, lang) => `[${articleFor(id, lang).title}](./${pathOf(id, lang)})`;
add('README.md', `# CAMBC 2026a documentation (local mirror)

Mirror of the online handbook at ${SITE}/game/docs and the Bot API reference at ${SITE}/game/api, synced ${date}. Regenerate with \`cd tools/docs-sync && npm install && node sync.mjs\`.

## Game rules

${ruleIds.map((id, i) => `${i + 1}. ${link(id)}`).join('\n')}

- ${link('glossary')}
- [Patch notes](./patch-notes.md)

## Champions

- ${link('champions')} (roster and stat comparison)
${champions.map(c => `- [${c.name}](./${pathOf(c.id)})`).join('\n')}

## Guides

| Guide | ${LANGS.map(l => langLabel[l]).join(' | ')} |
| --- | ${LANGS.map(() => '---').join(' | ')} |
${guideIds.map(id => `| ${articleFor(id, 'cpp').title} | ${LANGS.map(l => `[${langLabel[l]}](./${pathOf(id, l)})`).join(' | ')} |`).join('\n')}

## Bot API reference

${LANGS.map(l => `- [${langLabel[l]}](./api/${l}.md)`).join('\n')}

## LLM exports

The single-file Markdown exports the site offers for coding assistants: [llm/](./llm/README.md).

## Notes on this mirror

- Interactive diagrams are shown as the site's text description. Their full on-screen text (step-by-step walkthroughs, labels) is in a collapsible block under each one. Some of it adds rule detail not in the plain prose.
- Inline decorative icons are omitted. Images such as the sample map, terrain tiles and champion art are in [images/](./images/).
- API entries keep the signature, description, parameters and any hand-written examples. The site's auto-generated one-line examples are left out.
`);

// docs/ is fully generated: rebuild it from scratch so removed pages disappear.
rmSync(OUT, { recursive: true, force: true });
mkdirSync(join(OUT, 'images'), { recursive: true });
for (const [sitePath, file] of images) writeFileSync(join(OUT, 'images', file), await get(sitePath, true));
for (const [file, bytes] of patchImages) writeFileSync(join(OUT, 'images', file), bytes);

// Report anything the interpreter could not evaluate.
let problems = 0;
for (const [path, text] of files) {
  const dest = join(OUT, path);
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, text);
  const n = (text.match(/\[\[unsupported:[^\]]*\]\]|Unrendered block kind/g) ?? []).length;
  if (n) { problems += n; console.warn(`  ${path}: ${n} unevaluated fragment(s)`); }
}
console.log(`wrote ${files.size} Markdown files and ${images.size + patchImages.size} images to docs/${problems ? ` (${problems} problems)` : ''}`);

// Gaps that never reach the output text (e.g. an unevaluated assignment) still show up here.
// Unsupported markers from the interactive components' React code are expected and harmless.
if (unsupportedLog.size) console.log('interpreter gaps (construct: count):', Object.fromEntries(unsupportedLog));

// Sanity check: every API entry must appear as a heading with its signature in the site's own export.
// (An unsupported construct once rendered every entry as an empty string without leaving any marker.)
for (const lang of LANGS) {
  const name = `BotAPI${{ cpp: 'Cpp', rust: 'Rust', python: 'Python', ocaml: 'OCaml' }[lang]}.md`;
  const headings = (llmFiles[name].match(/^### /gm) ?? []).length;
  const missing = apiEntries[lang].filter(e => !llmFiles[name].includes(e.signature)).length;
  const ok = headings === apiEntries[lang].length && missing === 0;
  console.log(`check ${name}: ${ok ? 'ok' : 'FAILED'} (${headings}/${apiEntries[lang].length} entries, ${missing} signatures missing)`);
}
