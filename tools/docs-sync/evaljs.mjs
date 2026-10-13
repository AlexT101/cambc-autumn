// A deliberately tiny, side-effect-free interpreter for the data parts of a
// minified ES module bundle. It walks the acorn AST and evaluates literals,
// object/array/template expressions, simple arrow functions and a whitelist of
// pure built-in methods. Anything else becomes an Unsupported marker, so no
// code from the bundle is ever executed by the JS engine itself.
import { readFileSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import * as acorn from 'acorn';

// Every Unsupported created is tallied, so callers can detect silent gaps
// (e.g. an ignored assignment) even when no marker reaches the output.
export const unsupportedLog = new Map();
export class Unsupported {
  constructor(what) {
    this.what = what;
    if (!what.startsWith('cycle:')) unsupportedLog.set(what, (unsupportedLog.get(what) ?? 0) + 1);
  }
  toString() { return `[[unsupported:${this.what}]]`; }
}

const ARRAY_METHODS = new Set(['map', 'filter', 'flatMap', 'flat', 'find', 'findIndex', 'some', 'every', 'join',
  'concat', 'slice', 'includes', 'indexOf', 'reduce', 'reverse', 'at', 'entries', 'keys', 'values', 'forEach']);
const STRING_METHODS = new Set(['toLowerCase', 'toUpperCase', 'replace', 'replaceAll', 'trim', 'split', 'startsWith',
  'endsWith', 'includes', 'slice', 'repeat', 'padStart', 'padEnd', 'charAt', 'indexOf', 'match', 'concat', 'at',
  'toFixed', 'toString', 'trimEnd', 'trimStart', 'matchAll', 'test']);
const MAP_METHODS = new Set(['get', 'has', 'keys', 'values', 'entries']);

class Return { constructor(v) { this.v = v; } }

class Scope {
  constructor(parent, vars = new Map()) { this.parent = parent; this.vars = vars; }
  lookup(name) {
    for (let s = this; s; s = s.parent) if (s.vars.has(name)) return { found: true, value: s.vars.get(name) };
    return { found: false };
  }
  // Assign to an interpreter-local binding; module top-level state is never mutated.
  assign(name, value) {
    for (let s = this; s; s = s.parent) if (s.vars.has(name)) { s.vars.set(name, value); return true; }
    return false;
  }
}

function applyOp(op, a, b) {
  switch (op) {
    case '=': return b;
    case '+=': return a + b; case '-=': return a - b; case '*=': return a * b; case '/=': return a / b;
    case '||=': return a || b; case '&&=': return a && b; case '??=': return a ?? b;
    default: return new Unsupported(`assign:${op}`);
  }
}

const modules = new Map();
let cycleHits = 0; // values computed while a dependency cycle was cut short are not cached

export function loadModule(path) {
  if (modules.has(path)) return modules.get(path);
  const src = readFileSync(path, 'utf8');
  const ast = acorn.parse(src, { ecmaVersion: 'latest', sourceType: 'module' });
  const mod = { path, src, decls: new Map(), imports: new Map(), exports: new Map(), cache: new Map(), busy: new Set() };
  modules.set(path, mod);
  for (const node of ast.body) {
    if (node.type === 'ImportDeclaration') {
      const from = join(dirname(path), basename(node.source.value));
      for (const s of node.specifiers) {
        if (s.type === 'ImportSpecifier') mod.imports.set(s.local.name, { from, name: s.imported.name });
      }
    } else if (node.type === 'VariableDeclaration') {
      for (const d of node.declarations) if (d.id.type === 'Identifier') mod.decls.set(d.id.name, d.init);
    } else if (node.type === 'FunctionDeclaration') {
      mod.decls.set(node.id.name, node);
    } else if (node.type === 'ExportNamedDeclaration' && !node.declaration) {
      for (const s of node.specifiers) mod.exports.set(s.exported.name, s.local.name);
    }
  }
  mod.get = (name) => topLevel(mod, name);
  return mod;
}

function topLevel(mod, name) {
  if (mod.cache.has(name)) return mod.cache.get(name);
  if (mod.decls.has(name)) {
    if (mod.busy.has(name)) { cycleHits++; return new Unsupported(`cycle:${name}`); }
    mod.busy.add(name);
    const before = cycleHits;
    const node = mod.decls.get(name);
    const ctx = { mod, scope: new Scope(null) };
    const value = node == null ? undefined
      : node.type === 'FunctionDeclaration' ? makeFunction(node, ctx) : ev(node, ctx);
    mod.busy.delete(name);
    if (cycleHits === before) mod.cache.set(name, deepFreeze(value));
    return value;
  }
  if (mod.imports.has(name)) {
    const { from, name: exported } = mod.imports.get(name);
    let other;
    try { other = loadModule(from); } catch { return new Unsupported(`import:${basename(from)}:${exported}`); }
    const local = other.exports.get(exported);
    const before = cycleHits;
    const v = local ? topLevel(other, local) : new Unsupported(`export:${exported}`);
    if (cycleHits === before) mod.cache.set(name, v);
    return v;
  }
  return new Unsupported(`global:${name}`);
}

function deepFreeze(v) {
  if (v && typeof v === 'object' && !Object.isFrozen(v) && !(v instanceof Map) && !(v instanceof Set) && !(v instanceof RegExp)) {
    Object.freeze(v);
    for (const x of Object.values(v)) deepFreeze(x);
  }
  return v;
}

function makeFunction(node, ctx) {
  const fn = (...args) => {
    const scope = new Scope(ctx.scope);
    node.params.forEach((p, i) => bindPattern(p, p.type === 'RestElement' ? args.slice(i) : args[i], { ...ctx, scope }, scope));
    const inner = { ...ctx, scope };
    if (node.expression) return ev(node.body, inner);
    const r = execBlock(node.body.body, inner);
    return r instanceof Return ? r.v : undefined;
  };
  fn.__interp = true;
  return fn;
}

function bindPattern(p, value, ctx, scope) {
  switch (p.type) {
    case 'Identifier': scope.vars.set(p.name, value); return;
    case 'RestElement': bindPattern(p.argument, value, ctx, scope); return;
    case 'AssignmentPattern':
      bindPattern(p.left, value === undefined ? ev(p.right, { ...ctx, scope }) : value, ctx, scope); return;
    case 'ArrayPattern': {
      const arr = Array.isArray(value) ? value : [];
      p.elements.forEach((el, i) => { if (el) bindPattern(el, el.type === 'RestElement' ? arr.slice(i) : arr[i], ctx, scope); });
      return;
    }
    case 'ObjectPattern': {
      const obj = value && typeof value === 'object' ? value : {};
      for (const prop of p.properties) {
        if (prop.type === 'RestElement') continue;
        const key = prop.computed ? ev(prop.key, ctx) : (prop.key.name ?? prop.key.value);
        bindPattern(prop.value, obj[key], ctx, scope);
      }
      return;
    }
    default: scope.vars.set('__bad', new Unsupported(p.type));
  }
}

function execBlock(stmts, ctx) {
  for (const st of stmts) {
    const r = exec(st, ctx);
    if (r instanceof Return) return r;
  }
}

function exec(st, ctx) {
  switch (st.type) {
    case 'ReturnStatement': return new Return(st.argument ? ev(st.argument, ctx) : undefined);
    case 'VariableDeclaration':
      for (const d of st.declarations) bindPattern(d.id, d.init ? ev(d.init, ctx) : undefined, ctx, ctx.scope);
      return;
    case 'IfStatement':
      if (truthy(ev(st.test, ctx))) return exec(st.consequent, ctx);
      if (st.alternate) return exec(st.alternate, ctx);
      return;
    case 'BlockStatement': return execBlock(st.body, { ...ctx, scope: new Scope(ctx.scope) });
    case 'SwitchStatement': {
      const d = ev(st.discriminant, ctx);
      let matched = false;
      for (const c of st.cases) {
        if (!matched && (c.test === null || ev(c.test, ctx) === d)) matched = true;
        if (matched) { const r = execBlock(c.consequent, ctx); if (r) return r; if (c.consequent.some(s => s.type === 'BreakStatement')) return; }
      }
      return;
    }
    case 'ExpressionStatement': ev(st.expression, ctx); return;
    default: return new Return(new Unsupported(`stmt:${st.type}`));
  }
}

const truthy = (v) => !(v instanceof Unsupported) && !!v;

function callNative(target, method, args) {
  const wrap = (a) => (typeof a === 'function' && a.__interp) ? a : a;
  if (Array.isArray(target) && ARRAY_METHODS.has(method)) return target[method](...args.map(wrap));
  if (typeof target === 'string' && STRING_METHODS.has(method)) return target[method](...args);
  if (typeof target === 'number' && (method === 'toFixed' || method === 'toString')) return target[method](...args);
  if (typeof target === 'number' && method === 'toLocaleString') return target.toLocaleString('en-GB');
  if (target instanceof Map && MAP_METHODS.has(method)) return target[method](...args);
  if (target instanceof Set && (method === 'has' || method === 'values')) return target[method](...args);
  if (target instanceof RegExp && method === 'test') return target.test(...args);
  return new Unsupported(`method:${method}`);
}

const GLOBALS = {
  Object: { keys: Object.keys, values: Object.values, entries: Object.entries, fromEntries: Object.fromEntries, assign: (...a) => Object.assign({}, ...a) },
  Array: { from: Array.from, isArray: Array.isArray },
  Math: { max: Math.max, min: Math.min, round: Math.round, floor: Math.floor, ceil: Math.ceil, abs: Math.abs },
  JSON: { stringify: JSON.stringify },
  String, Number, Boolean,
};

export function ev(n, ctx) {
  switch (n.type) {
    case 'Literal': return n.regex ? new RegExp(n.regex.pattern, n.regex.flags) : n.value;
    case 'TemplateLiteral': {
      let s = n.quasis[0].value.cooked;
      for (let i = 0; i < n.expressions.length; i++) {
        const v = ev(n.expressions[i], ctx);
        s += (v instanceof Unsupported ? v.toString() : String(v)) + n.quasis[i + 1].value.cooked;
      }
      return s;
    }
    case 'Identifier': {
      if (n.name === 'undefined') return undefined;
      const l = ctx.scope.lookup(n.name);
      if (l.found) return l.value;
      if (ctx.mod.decls.has(n.name) || ctx.mod.imports.has(n.name)) return topLevel(ctx.mod, n.name);
      if (n.name in GLOBALS) return GLOBALS[n.name];
      return new Unsupported(`global:${n.name}`);
    }
    case 'ArrayExpression': {
      const out = [];
      for (const el of n.elements) {
        if (!el) { out.push(undefined); continue; }
        if (el.type === 'SpreadElement') {
          const v = ev(el.argument, ctx);
          if (v && typeof v[Symbol.iterator] === 'function' && typeof v !== 'string') out.push(...v);
          else out.push(new Unsupported('spread'));
        } else out.push(ev(el, ctx));
      }
      return out;
    }
    case 'ObjectExpression': {
      const out = {};
      for (const p of n.properties) {
        if (p.type === 'SpreadElement') { const v = ev(p.argument, ctx); if (v && typeof v === 'object') Object.assign(out, v); continue; }
        const key = p.computed ? ev(p.key, ctx) : (p.key.name ?? p.key.value);
        out[key] = (p.value.type === 'FunctionExpression' || p.value.type === 'ArrowFunctionExpression') ? makeFunction(p.value, ctx) : ev(p.value, ctx);
      }
      return out;
    }
    case 'ArrowFunctionExpression':
    case 'FunctionExpression': return makeFunction(n, ctx);
    case 'UnaryExpression': {
      if (n.operator === 'void') return undefined;
      const v = ev(n.argument, ctx);
      if (n.operator === '!') return v instanceof Unsupported ? v : !v;
      if (n.operator === '-') return -v;
      if (n.operator === '+') return +v;
      if (n.operator === 'typeof') return typeof v;
      return new Unsupported(`unary:${n.operator}`);
    }
    case 'BinaryExpression': {
      const a = ev(n.left, ctx), b = ev(n.right, ctx);
      switch (n.operator) {
        case '+': return a + b; case '-': return a - b; case '*': return a * b; case '/': return a / b; case '%': return a % b;
        case '===': return a === b; case '!==': return a !== b; case '==': return a == b; case '!=': return a != b;
        case '<': return a < b; case '>': return a > b; case '<=': return a <= b; case '>=': return a >= b;
        case 'in': return (b && typeof b === 'object') ? a in b : false;
        default: return new Unsupported(`binary:${n.operator}`);
      }
    }
    case 'LogicalExpression': {
      const a = ev(n.left, ctx);
      if (n.operator === '&&') return truthy(a) ? ev(n.right, ctx) : a;
      if (n.operator === '||') return truthy(a) ? a : ev(n.right, ctx);
      if (n.operator === '??') return (a === null || a === undefined) ? ev(n.right, ctx) : a;
      return new Unsupported('logical');
    }
    case 'ConditionalExpression': return truthy(ev(n.test, ctx)) ? ev(n.consequent, ctx) : ev(n.alternate, ctx);
    case 'SequenceExpression': { let v; for (const e of n.expressions) v = ev(e, ctx); return v; }
    case 'ChainExpression': return ev(n.expression, ctx);
    case 'MemberExpression': {
      const obj = ev(n.object, ctx);
      if (obj === null || obj === undefined) return n.optional ? undefined : new Unsupported('member-of-nullish');
      if (obj instanceof Unsupported) return obj;
      const key = n.computed ? ev(n.property, ctx) : n.property.name;
      if (key === 'length' && (Array.isArray(obj) || typeof obj === 'string')) return obj.length;
      if (obj instanceof Map && key === 'size') return obj.size;
      if (typeof obj === 'object' && !Array.isArray(obj) && !(obj instanceof Map) && Object.hasOwn(obj, key)) return obj[key];
      if (Array.isArray(obj) && typeof key === 'number') return obj[key];
      if (typeof obj === 'function' && !obj.__interp && key in obj) return obj[key];
      return undefined;
    }
    case 'CallExpression': {
      const args = [];
      for (const a of n.arguments) {
        if (a.type === 'SpreadElement') { const v = ev(a.argument, ctx); if (Array.isArray(v)) args.push(...v); else args.push(new Unsupported('spread-arg')); }
        else args.push(ev(a, ctx));
      }
      if (n.callee.type === 'MemberExpression') {
        const target = ev(n.callee.object, ctx);
        if (target instanceof Unsupported) return target;
        const method = n.callee.computed ? ev(n.callee.property, ctx) : n.callee.property.name;
        if (target && typeof target === 'object' && !Array.isArray(target) && !(target instanceof Map) && !(target instanceof Set)
            && !(target instanceof RegExp) && typeof target[method] === 'function') {
          return target[method](...args); // GLOBALS helpers or interpreted functions stored on data objects
        }
        return callNative(target, method, args);
      }
      const fn = ev(n.callee, ctx);
      if (typeof fn === 'function') return fn(...args);
      return new Unsupported(`call:${n.callee.type === 'Identifier' ? n.callee.name : n.callee.type}`);
    }
    case 'NewExpression': {
      const args = n.arguments.map(a => ev(a, ctx));
      if (n.callee.type === 'Identifier' && n.callee.name === 'Map') return new Map(args[0] ?? []);
      if (n.callee.type === 'Identifier' && n.callee.name === 'Set') return new Set(args[0] ?? []);
      return new Unsupported('new');
    }
    case 'AssignmentExpression':
    case 'UpdateExpression': {
      const target = n.type === 'UpdateExpression' ? n.argument : n.left;
      const op = n.type === 'UpdateExpression' ? (n.operator === '++' ? '+=' : '-=') : n.operator;
      const rhs = () => (n.type === 'UpdateExpression' ? 1 : ev(n.right, ctx));
      if (target.type === 'Identifier') {
        const cur = ctx.scope.lookup(target.name);
        if (!cur.found) return new Unsupported(`assign-global:${target.name}`);
        const v = applyOp(op, cur.value, rhs());
        ctx.scope.assign(target.name, v);
        return n.type === 'UpdateExpression' && !n.prefix ? cur.value : v;
      }
      if (target.type === 'MemberExpression') {
        const obj = ev(target.object, ctx);
        const key = target.computed ? ev(target.property, ctx) : target.property.name;
        // Only objects created by the interpreter during this call are writable; top-level data stays frozen.
        if (!obj || typeof obj !== 'object' || obj instanceof Unsupported || Object.isFrozen(obj)) return new Unsupported('assign-member');
        const v = applyOp(op, obj[key], rhs());
        obj[key] = v;
        return v;
      }
      return new Unsupported(`assign:${target.type}`);
    }
    case 'TaggedTemplateExpression': return new Unsupported('tagged-template');
    default: return new Unsupported(n.type);
  }
}
