//! Native mode, part 1: translates a bot's wasm into C that meters fuel exactly as wasmtime 49.0.2 does with
//! cambc's configuration, for clang to compile into a shared library (native.rs runs it).
//!
//! Fuel (wasmtime-internal-cranelift's func_environ.rs, mirrored operator by operator):
//! - every reachable operator costs 1, except nop, drop, block, loop, unreachable, return, else, end and
//!   memory.grow (0); the cost is buffered and added to the function's fuel variable at the same points as
//!   wasmtime (before calls, returns, throws, unreachable, loop, if, br*, end, else);
//! - the variable is saved to the instance before calls/returns/throws/unreachable and reloaded after calls and
//!   on entering a catch handler, so host calls, traps and handlers see the same counter;
//! - it is checked (out of gas when >= 0) at function entry, at every loop header and after a bulk memory
//!   operation whose size-proportional cost was deferred: which bulk operations those are depends on Cranelift's
//!   SSA values, so the translation asks the vendored Cranelift (`cambc_hook`) instead of guessing.
use anyhow::{anyhow, bail, Context, Result};
use std::collections::{BTreeSet, HashMap};
use std::fmt::Write as _;
use wasmparser::{BlockType, Catch, CompositeInnerType, DataKind, ElementItems, ElementKind, ExternalKind, Operator, Parser, Payload, TypeRef, ValType};

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, PartialOrd, Ord)]
enum T {
    I,
    J,
    F,
    D,
    V,
    E,
}

impl T {
    fn of(v: ValType) -> T {
        match v {
            ValType::I32 => T::I,
            ValType::I64 => T::J,
            ValType::F32 => T::F,
            ValType::F64 => T::D,
            ValType::V128 => T::V,
            ValType::Ref(_) => T::E,
        }
    }
    fn c(self) -> &'static str {
        match self {
            T::I => "u32",
            T::J => "u64",
            T::F => "f32",
            T::D => "f64",
            T::V => "v128",
            T::E => "u64",
        }
    }
    fn ch(self) -> char {
        match self {
            T::I => 'i',
            T::J => 'j',
            T::F => 'f',
            T::D => 'd',
            T::V => 'v',
            T::E => 'e',
        }
    }
    fn zero(self) -> &'static str {
        match self {
            T::V => "(v128){0}",
            _ => "0",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
struct Sig {
    params: Vec<T>,
    results: Vec<T>,
}

/// Bulk-memory fuel placement reported by Cranelift: (kind, cost per unit, constant units).
pub type BulkLog = HashMap<u32, (u8, u8, i64)>;

pub struct CModule {
    /// Shared declarations (included by every unit).
    pub header: String,
    /// Translation units: the module descriptor first, then function bodies.
    pub units: Vec<String>,
}

struct Module<'a> {
    types: Vec<Option<Sig>>,
    canon: Vec<u32>,
    imports: Vec<(String, String, u32)>,
    funcs: Vec<u32>,
    nimp: usize,
    table: Option<u64>,
    mem: (u64, Option<u64>),
    tags: Vec<u32>,
    globals: Vec<(T, bool, u64)>,
    start: Option<u32>,
    elems: Vec<(u32, Vec<u32>)>,
    data: Vec<(u32, &'a [u8])>,
    bodies: Vec<wasmparser::FunctionBody<'a>>,
    may_throw: Vec<bool>,
}

fn const_expr(e: &wasmparser::ConstExpr) -> Result<u64> {
    let mut r = e.get_operators_reader();
    let v = match r.read()? {
        Operator::I32Const { value } => value as u32 as u64,
        Operator::I64Const { value } => value as u64,
        Operator::F32Const { value } => value.bits() as u64,
        Operator::F64Const { value } => value.bits(),
        o => bail!("unsupported constant expression {o:?}"),
    };
    match r.read()? {
        Operator::End => Ok(v),
        o => bail!("unsupported constant expression ending {o:?}"),
    }
}

fn parse(wasm: &[u8]) -> Result<Module<'_>> {
    let mut m = Module {
        types: vec![],
        canon: vec![],
        imports: vec![],
        funcs: vec![],
        nimp: 0,
        table: None,
        mem: (0, None),
        tags: vec![],
        globals: vec![],
        start: None,
        elems: vec![],
        data: vec![],
        bodies: vec![],
        may_throw: vec![],
    };
    let mut sigs: HashMap<Sig, u32> = HashMap::new();
    for p in Parser::new(0).parse_all(wasm) {
        match p? {
            Payload::TypeSection(r) => {
                for rg in r {
                    for st in rg?.into_types() {
                        let sig = match &st.composite_type.inner {
                            CompositeInnerType::Func(ft) => Some(Sig {
                                params: ft.params().iter().map(|v| T::of(*v)).collect(),
                                results: ft.results().iter().map(|v| T::of(*v)).collect(),
                            }),
                            _ => None,
                        };
                        let n = sigs.len() as u32;
                        let c = sig.as_ref().map(|s| *sigs.entry(s.clone()).or_insert(n)).unwrap_or(u32::MAX);
                        m.types.push(sig);
                        m.canon.push(c);
                    }
                }
            }
            Payload::ImportSection(r) => {
                for imp in r.into_imports() {
                    let imp = imp?;
                    match imp.ty {
                        TypeRef::Func(t) => {
                            m.imports.push((imp.module.to_string(), imp.name.to_string(), t));
                            m.funcs.push(t);
                        }
                        _ => bail!("unsupported import {}::{}", imp.module, imp.name),
                    }
                }
                m.nimp = m.funcs.len();
            }
            Payload::FunctionSection(r) => {
                for t in r {
                    m.funcs.push(t?);
                }
            }
            Payload::TableSection(r) => {
                for t in r {
                    let t = t?;
                    if m.table.is_some() || !t.ty.element_type.is_func_ref() {
                        bail!("unsupported table");
                    }
                    m.table = Some(t.ty.initial);
                }
            }
            Payload::MemorySection(r) => {
                for mt in r {
                    let mt = mt?;
                    if mt.memory64 || mt.shared || mt.page_size_log2.is_some() {
                        bail!("unsupported memory");
                    }
                    m.mem = (mt.initial, mt.maximum);
                }
            }
            Payload::TagSection(r) => {
                for t in r {
                    let t = t?;
                    let sig = m.types[t.func_type_idx as usize].as_ref().ok_or_else(|| anyhow!("tag type"))?;
                    if sig.params != [T::I] || !sig.results.is_empty() {
                        bail!("unsupported tag type");
                    }
                    m.tags.push(t.func_type_idx);
                }
            }
            Payload::GlobalSection(r) => {
                for g in r {
                    let g = g?;
                    let t = T::of(g.ty.content_type);
                    if t == T::V || t == T::E {
                        bail!("unsupported global type");
                    }
                    m.globals.push((t, g.ty.mutable, const_expr(&g.init_expr)?));
                }
            }
            Payload::ExportSection(r) => {
                for e in r {
                    let e = e?;
                    if e.name == "_start" && e.kind == ExternalKind::Func {
                        m.start = Some(e.index);
                    }
                }
            }
            Payload::StartSection { .. } => bail!("unsupported start section"),
            Payload::ElementSection(r) => {
                for e in r {
                    let e = e?;
                    let ElementKind::Active { table_index, offset_expr } = e.kind else { bail!("unsupported element segment") };
                    if table_index.unwrap_or(0) != 0 {
                        bail!("unsupported element segment table");
                    }
                    let off = const_expr(&offset_expr)? as u32;
                    let items = match e.items {
                        ElementItems::Functions(r) => r.into_iter().collect::<std::result::Result<Vec<u32>, _>>()?,
                        ElementItems::Expressions(_, r) => {
                            let mut v = vec![];
                            for ce in r {
                                let ce = ce?;
                                let mut rr = ce.get_operators_reader();
                                match rr.read()? {
                                    Operator::RefFunc { function_index } => v.push(function_index),
                                    o => bail!("unsupported element {o:?}"),
                                }
                            }
                            v
                        }
                    };
                    m.elems.push((off, items));
                }
            }
            Payload::DataSection(r) => {
                for d in r {
                    let d = d?;
                    let DataKind::Active { memory_index: 0, offset_expr } = d.kind else { bail!("unsupported data segment") };
                    m.data.push((const_expr(&offset_expr)? as u32, d.data));
                }
            }
            Payload::DataCountSection { .. } => {}
            Payload::CodeSectionEntry(b) => m.bodies.push(b),
            Payload::CustomSection(_) | Payload::Version { .. } | Payload::End(_) | Payload::CodeSectionStart { .. } => {}
            other => bail!("unsupported section {other:?}"),
        }
    }
    if m.start.is_none() {
        bail!("no _start export");
    }
    for (i, &t) in m.funcs.iter().enumerate() {
        let s = m.types[t as usize].as_ref().ok_or_else(|| anyhow!("function type"))?;
        if s.results.len() > 1 {
            bail!("function {i} returns several values");
        }
    }
    // Which functions can let an exception escape: they throw, or call one that can.
    let n = m.funcs.len();
    let mut throws = vec![false; n];
    let mut calls: Vec<Vec<u32>> = vec![vec![]; n];
    let mut indirect = vec![false; n];
    for (k, b) in m.bodies.iter().enumerate() {
        let f = m.nimp + k;
        let mut r = b.get_operators_reader()?;
        while !r.eof() {
            match r.read()? {
                Operator::Throw { .. } | Operator::ThrowRef => throws[f] = true,
                Operator::Call { function_index } => calls[f].push(function_index),
                Operator::CallIndirect { .. } => indirect[f] = true,
                Operator::ReturnCall { .. } | Operator::ReturnCallIndirect { .. } | Operator::CallRef { .. } => bail!("unsupported call kind"),
                _ => {}
            }
        }
    }
    let table_funcs: Vec<u32> = m.elems.iter().flat_map(|(_, v)| v.iter().copied()).collect();
    loop {
        let any_table = table_funcs.iter().any(|&f| throws[f as usize]);
        let mut changed = false;
        for f in m.nimp..n {
            if throws[f] {
                continue;
            }
            if (indirect[f] && any_table) || calls[f].iter().any(|&c| throws[c as usize]) {
                throws[f] = true;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    m.may_throw = throws;
    Ok(m)
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum K {
    Func,
    Block,
    Loop,
    If,
    Try,
}

struct Frame {
    kind: K,
    id: u32,
    base: usize,
    params: Vec<T>,
    results: Vec<T>,
    /// wasmtime's exit_is_branched_to (never for loops).
    branched: bool,
    /// Pushed while unreachable: a placeholder, everything inside stays unreachable.
    dead: bool,
    head_reachable: bool,
    cons_end: Option<bool>,
    /// If with parameters: copies of them for the else branch.
    saved: Vec<String>,
}

struct Fx<'m, 'a> {
    m: &'m Module<'a>,
    bulk: &'m BulkLog,
    body: String,
    decls: BTreeSet<(usize, T)>,
    extra: Vec<String>,
    stack: Vec<T>,
    ctrl: Vec<Frame>,
    reachable: bool,
    pend: i64,
    next: u32,
    handlers: Vec<String>,
    uses_hp: bool,
    ret: Option<T>,
    locals: Vec<T>,
    fid: usize,
    /// The previous operator was a load: where its line starts in `body`, and a volatile access to the same bytes.
    last_load: Option<(usize, String)>,
}

/// FASTRUNNER_TRACE_SITES=1: record each import call's site in `fr_site` (host.rs's fuel trace).
pub fn trace_sites() -> bool {
    std::env::var_os("FASTRUNNER_TRACE_SITES").is_some()
}

fn op_cost(op: &Operator) -> i64 {
    match op {
        Operator::Nop
        | Operator::Drop
        | Operator::Block { .. }
        | Operator::Loop { .. }
        | Operator::Unreachable
        | Operator::Return
        | Operator::Else
        | Operator::End
        | Operator::MemoryGrow { .. } => 0,
        _ => 1,
    }
}

fn f32c(bits: u32) -> String {
    format!("f32_bits(0x{bits:08x}u)")
}
fn f64c(bits: u64) -> String {
    format!("f64_bits(0x{bits:016x}ull)")
}

impl<'m, 'a> Fx<'m, 'a> {
    fn slot(&mut self, d: usize, t: T) -> String {
        self.decls.insert((d, t));
        format!("s{d}{}", t.ch())
    }
    fn push(&mut self, t: T) -> String {
        let d = self.stack.len();
        self.stack.push(t);
        self.slot(d, t)
    }
    fn pop(&mut self) -> String {
        let t = self.stack.pop().expect("stack underflow");
        let d = self.stack.len();
        self.slot(d, t)
    }
    fn pop_t(&mut self) -> (String, T) {
        let t = *self.stack.last().expect("stack underflow");
        (self.pop(), t)
    }
    fn peek(&mut self) -> String {
        let t = *self.stack.last().unwrap();
        let d = self.stack.len() - 1;
        self.slot(d, t)
    }
    fn line(&mut self, s: &str) {
        self.body.push_str("  ");
        self.body.push_str(s);
        self.body.push('\n');
    }
    fn flush(&mut self) {
        if self.pend != 0 {
            let p = self.pend;
            self.line(&format!("fuel += {p};"));
            self.pend = 0;
        }
    }
    fn save(&mut self) {
        self.line("I->fuel = fuel;");
    }
    fn check(&mut self) {
        self.flush();
        self.line("FUEL_CHECK();");
    }
    fn label(&mut self) -> u32 {
        self.next += 1;
        self.next
    }
    fn handler(&mut self) -> String {
        for f in self.ctrl.iter().rev() {
            if f.kind == K::Try && !f.dead {
                return format!("H{}", f.id);
            }
        }
        self.uses_hp = true;
        "HP".into()
    }
    fn block_type(&self, bt: BlockType) -> (Vec<T>, Vec<T>) {
        match bt {
            BlockType::Empty => (vec![], vec![]),
            BlockType::Type(v) => (vec![], vec![T::of(v)]),
            BlockType::FuncType(i) => {
                let s = self.m.types[i as usize].as_ref().unwrap();
                (s.params.clone(), s.results.clone())
            }
        }
    }
    fn push_frame(&mut self, kind: K, params: Vec<T>, results: Vec<T>) -> u32 {
        let id = self.label();
        let base = self.stack.len() - params.len();
        self.ctrl.push(Frame { kind, id, base, params, results, branched: false, dead: false, head_reachable: true, cons_end: None, saved: vec![] });
        id
    }
    /// Branch target at relative depth: (label, value types, base slot); marks the exit branched to.
    fn target(&mut self, rel: u32) -> (String, Vec<T>, usize) {
        let i = self.ctrl.len() - 1 - rel as usize;
        let f = &mut self.ctrl[i];
        match f.kind {
            K::Loop => (format!("L{}t", f.id), f.params.clone(), f.base),
            K::Func => {
                f.branched = true;
                ("Lret".into(), f.results.clone(), f.base)
            }
            _ => {
                f.branched = true;
                (format!("L{}", f.id), f.results.clone(), f.base)
            }
        }
    }
    /// Copies the top `types.len()` stack values into the target's slots.
    fn copies(&mut self, types: &[T], base: usize) -> String {
        let n = types.len();
        let h = self.stack.len();
        let mut s = String::new();
        for (k, &t) in types.iter().enumerate() {
            let src = self.slot(h - n + k, t);
            let dst = self.slot(base + k, t);
            if src != dst {
                write!(s, "{dst} = {src}; ").unwrap();
            }
        }
        s
    }
    fn bin(&mut self, r: T, f: &str) {
        let b = self.pop();
        let a = self.pop();
        let d = self.push(r);
        let e = f.replace("{a}", &a).replace("{b}", &b);
        self.line(&format!("{d} = {e};"));
    }
    fn un(&mut self, r: T, f: &str) {
        let a = self.pop();
        let d = self.push(r);
        let e = f.replace("{a}", &a);
        self.line(&format!("{d} = {e};"));
    }
    fn addr(&self, a: &str, off: u64) -> String {
        if off == 0 {
            format!("M + (u64){a}")
        } else {
            format!("M + (u64){a} + {off}ull")
        }
    }
    // An i32 address plus any i32 offset and the access stays inside the 8 GiB + 2-page reservation, so even a
    // huge offset only faults (traps) when executed.
    fn load(&mut self, r: T, ty: &str, conv: &str, ma: &wasmparser::MemArg) -> Result<()> {
        let a = self.pop();
        let d = self.push(r);
        self.last_load = Some((self.body.len(), format!("TOUCH({ty}, {a}, {}ull);", ma.offset)));
        self.line(&format!("{d} = {conv}LD({ty}, {a}, {}ull);", ma.offset));
        Ok(())
    }
    fn store(&mut self, ty: &str, ma: &wasmparser::MemArg) -> Result<()> {
        let v = self.pop();
        let a = self.pop();
        self.line(&format!("ST({ty}, {a}, {}ull, ({ty}){v});", ma.offset));
        Ok(())
    }
    fn vload(&mut self, f: &str, ma: &wasmparser::MemArg) -> Result<()> {
        let a = self.pop();
        let d = self.push(T::V);
        let p = self.addr(&a, ma.offset);
        let ty = match f {
            "v_load" => "v128",
            "v_load8_splat" => "u8",
            "v_load16_splat" => "u16",
            "v_load32_splat" | "v_load32_zero" => "u32",
            _ => "u64",
        };
        self.last_load = Some((self.body.len(), format!("TOUCH({ty}, {a}, {}ull);", ma.offset)));
        self.line(&format!("{d} = {f}({p});"));
        Ok(())
    }
    fn call(&mut self, sig: &Sig, callee: String, may_throw: bool) {
        let n = sig.params.len();
        let h = self.stack.len();
        let mut args = vec!["I".to_string()];
        for k in 0..n {
            let t = self.stack[h - n + k];
            args.push(self.slot(h - n + k, t));
        }
        self.stack.truncate(h - n);
        let call = format!("{callee}({})", args.join(", "));
        match sig.results.first() {
            Some(&t) => {
                let d = self.push(t);
                self.line(&format!("{d} = {call};"));
            }
            None => self.line(&format!("{call};")),
        }
        self.line("fuel = I->fuel;");
        if may_throw {
            let h = self.handler();
            self.line(&format!("if (UNLIKELY(I->exn)) goto {h};"));
        }
    }
    fn fn_ptr_type(sig: &Sig) -> String {
        let r = sig.results.first().map_or("void", |t| t.c());
        let mut p = vec!["Inst*".to_string()];
        p.extend(sig.params.iter().map(|t| t.c().to_string()));
        format!("{r}(*)({})", p.join(", "))
    }

    /// Translates one operator (wasmtime's before_translate_operator + translate_operator + after).
    fn op(&mut self, op: &Operator, pos: u32) -> Result<()> {
        let last_load = self.last_load.take();
        if !self.reachable {
            return self.unreachable_op(op);
        }
        self.pend += op_cost(op);
        use Operator as O;
        match op {
            O::Unreachable => {
                self.flush();
                self.save();
                self.line("fr_trap(I, T_UNREACHABLE);");
                self.reachable = false;
            }
            O::Nop => {}
            O::Block { blockty } => {
                let (p, r) = self.block_type(*blockty);
                self.push_frame(K::Block, p, r);
            }
            O::Loop { blockty } => {
                self.flush();
                let (p, r) = self.block_type(*blockty);
                let id = self.push_frame(K::Loop, p, r);
                self.line(&format!("L{id}t:;"));
                self.check();
            }
            O::If { blockty } => {
                self.flush();
                let c = self.pop();
                let (p, r) = self.block_type(*blockty);
                let id = self.push_frame(K::If, p.clone(), r);
                let base = self.ctrl.last().unwrap().base;
                let mut saved = vec![];
                for (k, &t) in p.iter().enumerate() {
                    let src = self.slot(base + k, t);
                    let name = format!("p{id}_{k}");
                    self.extra.push(format!("{} {name};", t.c()));
                    self.line(&format!("{name} = {src};"));
                    saved.push(name);
                }
                self.ctrl.last_mut().unwrap().saved = saved;
                self.line(&format!("if (!{c}) goto E{id};"));
            }
            O::Else => {
                self.flush();
                let f = self.ctrl.last_mut().unwrap();
                f.cons_end = Some(true);
                let id = f.id;
                f.branched = true; // the consequent jumps to the end
                let base = f.base;
                let params = f.params.clone();
                let saved = f.saved.clone();
                self.line(&format!("goto L{id};"));
                self.else_entry(id, base, &params, &saved);
            }
            O::End => {
                self.flush();
                self.end_frame()?;
            }
            O::Br { relative_depth } => {
                self.flush();
                let (l, ts, base) = self.target(*relative_depth);
                let c = self.copies(&ts, base);
                self.line(&format!("{c}goto {l};"));
                self.reachable = false;
            }
            O::BrIf { relative_depth } => {
                self.flush();
                let c = self.pop();
                let (l, ts, base) = self.target(*relative_depth);
                let cp = self.copies(&ts, base);
                self.line(&format!("if ({c}) {{ {cp}goto {l}; }}"));
            }
            O::BrTable { targets } => {
                self.flush();
                let i = self.pop();
                let mut s = format!("switch ({i}) {{ ");
                for (k, d) in targets.targets().enumerate() {
                    let (l, ts, base) = self.target(d?);
                    let cp = self.copies(&ts, base);
                    write!(s, "case {k}: {cp}goto {l}; ").unwrap();
                }
                let (l, ts, base) = self.target(targets.default());
                let cp = self.copies(&ts, base);
                write!(s, "default: {cp}goto {l}; }}").unwrap();
                self.line(&s);
                self.reachable = false;
            }
            O::Return => {
                self.flush();
                self.save();
                match self.ret {
                    Some(_) => {
                        let v = self.peek();
                        self.line(&format!("return {v};"));
                    }
                    None => self.line("return;"),
                }
                self.reachable = false;
            }
            O::Call { function_index } => {
                self.flush();
                self.save();
                let f = *function_index as usize;
                let sig = self.m.types[self.m.funcs[f] as usize].clone().unwrap();
                if f < self.m.nimp {
                    if trace_sites() {
                        let fid = self.fid;
                        self.line(&format!("fr_site = ((u64){fid}u << 32) | {pos}u;"));
                    }
                    let callee = format!("(({})IMPS[{f}])", Self::fn_ptr_type(&sig));
                    self.call(&sig, callee, false);
                    // cambc 5.0.1's host trampolines run out_of_gas as soon as a host call returns with the chunk spent.
                    self.line("FUEL_CHECK();");
                } else {
                    let mt = self.m.may_throw[f];
                    self.call(&sig, format!("wf{f}"), mt);
                }
            }
            O::CallIndirect { type_index, table_index } => {
                if *table_index != 0 {
                    bail!("call_indirect table");
                }
                self.flush();
                self.save();
                let sig = self.m.types[*type_index as usize].clone().unwrap();
                let idx = self.pop();
                let canon = self.m.canon[*type_index as usize];
                let ft = Self::fn_ptr_type(&sig);
                self.line(&format!(
                    "{{ if (UNLIKELY({idx} >= TBL_N)) fr_trap(I, T_TABLE_OOB); if (UNLIKELY(!TBL[{idx}].f)) fr_trap(I, T_NULL_CALL); if (UNLIKELY(TBL[{idx}].sig != {canon}u)) fr_trap(I, T_SIG); }}"
                ));
                let any = self.m.elems.iter().flat_map(|(_, v)| v.iter()).any(|&f| self.m.may_throw[f as usize]);
                self.call(&sig, format!("(({ft})TBL[{idx}].f)"), any);
            }
            O::Drop => {
                self.pop();
                // Cranelift keeps a dropped load (it can trap); clang would delete it.
                if let Some((at, touch)) = last_load {
                    self.body.truncate(at);
                    self.line(&touch);
                }
            }
            O::Select | O::TypedSelect { .. } => {
                let c = self.pop();
                let b = self.pop();
                let (a, t) = self.pop_t();
                let d = self.push(t);
                self.line(&format!("{d} = {c} ? {a} : {b};"));
            }
            O::LocalGet { local_index } => {
                let t = self.local_t(*local_index);
                let d = self.push(t);
                self.line(&format!("{d} = l{local_index};"));
            }
            O::LocalSet { local_index } => {
                let v = self.pop();
                self.line(&format!("l{local_index} = {v};"));
            }
            O::LocalTee { local_index } => {
                let v = self.peek();
                self.line(&format!("l{local_index} = {v};"));
            }
            O::GlobalGet { global_index } => {
                let (t, mutable, init) = self.m.globals[*global_index as usize];
                let d = self.push(t);
                let e = if mutable {
                    match t {
                        T::I => format!("(u32)I->g[{global_index}]"),
                        T::J => format!("I->g[{global_index}]"),
                        T::F => format!("f32_bits((u32)I->g[{global_index}])"),
                        _ => format!("f64_bits(I->g[{global_index}])"),
                    }
                } else {
                    match t {
                        T::I => format!("0x{:08x}u", init as u32),
                        T::J => format!("0x{init:016x}ull"),
                        T::F => f32c(init as u32),
                        _ => f64c(init),
                    }
                };
                self.line(&format!("{d} = {e};"));
            }
            O::GlobalSet { global_index } => {
                let (t, _, _) = self.m.globals[*global_index as usize];
                let v = self.pop();
                let e = match t {
                    T::I => format!("(u64){v}"),
                    T::J => v.clone(),
                    T::F => format!("(u64)bits_f32({v})"),
                    _ => format!("bits_f64({v})"),
                };
                self.line(&format!("I->g[{global_index}] = {e};"));
            }
            O::I32Load { memarg } => self.load(T::I, "u32", "", memarg)?,
            O::I64Load { memarg } => self.load(T::J, "u64", "", memarg)?,
            O::F32Load { memarg } => self.load(T::F, "f32", "", memarg)?,
            O::F64Load { memarg } => self.load(T::D, "f64", "", memarg)?,
            O::I32Load8S { memarg } => self.load(T::I, "i8", "(u32)(i32)", memarg)?,
            O::I32Load8U { memarg } => self.load(T::I, "u8", "(u32)", memarg)?,
            O::I32Load16S { memarg } => self.load(T::I, "i16", "(u32)(i32)", memarg)?,
            O::I32Load16U { memarg } => self.load(T::I, "u16", "(u32)", memarg)?,
            O::I64Load8S { memarg } => self.load(T::J, "i8", "(u64)(i64)", memarg)?,
            O::I64Load8U { memarg } => self.load(T::J, "u8", "(u64)", memarg)?,
            O::I64Load16S { memarg } => self.load(T::J, "i16", "(u64)(i64)", memarg)?,
            O::I64Load16U { memarg } => self.load(T::J, "u16", "(u64)", memarg)?,
            O::I64Load32S { memarg } => self.load(T::J, "i32", "(u64)(i64)", memarg)?,
            O::I64Load32U { memarg } => self.load(T::J, "u32", "(u64)", memarg)?,
            O::I32Store { memarg } => self.store("u32", memarg)?,
            O::I64Store { memarg } => self.store("u64", memarg)?,
            O::F32Store { memarg } => self.store("f32", memarg)?,
            O::F64Store { memarg } => self.store("f64", memarg)?,
            O::I32Store8 { memarg } | O::I64Store8 { memarg } => self.store("u8", memarg)?,
            O::I32Store16 { memarg } | O::I64Store16 { memarg } => self.store("u16", memarg)?,
            O::I64Store32 { memarg } => self.store("u32", memarg)?,
            O::MemorySize { .. } => {
                let d = self.push(T::I);
                self.line(&format!("{d} = (u32)(I->size >> 16);"));
            }
            O::MemoryGrow { .. } => {
                let a = self.pop();
                let d = self.push(T::I);
                self.line(&format!("{d} = fr_memory_grow(I, {a});"));
            }
            O::MemoryCopy { .. } | O::MemoryFill { .. } => {
                let n = self.pop();
                let s = self.pop();
                let d = self.pop();
                let (kind, cost, units) = *self.bulk.get(&pos).ok_or_else(|| anyhow!("no Cranelift fuel record for the bulk operation at {pos}"))?;
                let f = if matches!(op, O::MemoryCopy { .. }) { "mem_copy" } else { "mem_fill" };
                match kind {
                    // constant size, charged before the operation, no check
                    0 => {
                        self.pend += units * cost as i64;
                        self.line(&format!("{f}(I, M, {d}, {s}, {n});"));
                    }
                    // constant size charged after the operation, then a check
                    1 => {
                        self.line(&format!("{f}(I, M, {d}, {s}, {n});"));
                        self.pend += units * cost as i64;
                        self.check();
                    }
                    _ => {
                        self.line(&format!("{f}(I, M, {d}, {s}, {n});"));
                        self.flush();
                        self.line(&format!("fuel += (i64)((u64){n} * {cost}u);"));
                        self.check();
                    }
                }
            }
            O::I32Const { value } => {
                let d = self.push(T::I);
                self.line(&format!("{d} = 0x{:08x}u;", *value as u32));
            }
            O::I64Const { value } => {
                let d = self.push(T::J);
                self.line(&format!("{d} = 0x{:016x}ull;", *value as u64));
            }
            O::F32Const { value } => {
                let d = self.push(T::F);
                self.line(&format!("{d} = {};", f32c(value.bits())));
            }
            O::F64Const { value } => {
                let d = self.push(T::D);
                self.line(&format!("{d} = {};", f64c(value.bits())));
            }
            O::V128Const { value } => {
                let b = value.bytes();
                let lo = u64::from_le_bytes(b[0..8].try_into().unwrap());
                let hi = u64::from_le_bytes(b[8..16].try_into().unwrap());
                let d = self.push(T::V);
                self.line(&format!("{d} = v128_make(0x{lo:016x}ull, 0x{hi:016x}ull);"));
            }
            O::RefNull { .. } => {
                let d = self.push(T::E);
                self.line(&format!("{d} = 0;"));
            }
            O::RefIsNull => self.un(T::I, "{a} == 0"),

            // exceptions
            O::TryTable { try_table } => {
                let (p, r) = self.block_type(try_table.ty);
                let outer = self.handler();
                let mut code = String::new();
                let tmp_id = self.next + 1;
                write!(code, "H{tmp_id}: {{ u64 e = I->exn;\n").unwrap();
                for c in &try_table.catches {
                    match *c {
                        Catch::One { tag, label } => {
                            let (l, ts, base) = self.target(label);
                            let dst = self.slot(base, ts[0]);
                            write!(code, "  if (EXN_TAG(e) == {tag}u) {{ I->exn = 0; fuel = I->fuel; {dst} = EXN_PAY(e); goto {l}; }}\n").unwrap();
                        }
                        Catch::OneRef { tag, label } => {
                            let (l, ts, base) = self.target(label);
                            let d0 = self.slot(base, ts[0]);
                            let d1 = self.slot(base + 1, ts[1]);
                            write!(code, "  if (EXN_TAG(e) == {tag}u) {{ I->exn = 0; fuel = I->fuel; {d0} = EXN_PAY(e); {d1} = e; goto {l}; }}\n").unwrap();
                        }
                        Catch::All { label } => {
                            let (l, _, _) = self.target(label);
                            write!(code, "  {{ I->exn = 0; fuel = I->fuel; goto {l}; }}\n").unwrap();
                        }
                        Catch::AllRef { label } => {
                            let (l, ts, base) = self.target(label);
                            let d0 = self.slot(base, ts[0]);
                            write!(code, "  {{ I->exn = 0; fuel = I->fuel; {d0} = e; goto {l}; }}\n").unwrap();
                        }
                    }
                }
                write!(code, "  goto {outer};\n}}\n").unwrap();
                let id = self.push_frame(K::Try, p, r);
                assert_eq!(id, tmp_id);
                self.handlers.push(code);
            }
            O::Throw { tag_index } => {
                self.flush();
                self.save();
                let v = self.pop();
                let h = self.handler();
                self.line(&format!("I->exn = EXN_MAKE({tag_index}u, {v}); goto {h};"));
                self.reachable = false;
            }
            O::ThrowRef => {
                self.flush();
                self.save();
                let v = self.pop();
                let h = self.handler();
                self.line(&format!("if (UNLIKELY(!{v})) fr_trap(I, T_NULL_REF); I->exn = {v}; goto {h};"));
                self.reachable = false;
            }

            // i32
            O::I32Eqz => self.un(T::I, "{a} == 0"),
            O::I32Eq => self.bin(T::I, "{a} == {b}"),
            O::I32Ne => self.bin(T::I, "{a} != {b}"),
            O::I32LtS => self.bin(T::I, "(i32){a} < (i32){b}"),
            O::I32LtU => self.bin(T::I, "{a} < {b}"),
            O::I32GtS => self.bin(T::I, "(i32){a} > (i32){b}"),
            O::I32GtU => self.bin(T::I, "{a} > {b}"),
            O::I32LeS => self.bin(T::I, "(i32){a} <= (i32){b}"),
            O::I32LeU => self.bin(T::I, "{a} <= {b}"),
            O::I32GeS => self.bin(T::I, "(i32){a} >= (i32){b}"),
            O::I32GeU => self.bin(T::I, "{a} >= {b}"),
            O::I32Clz => self.un(T::I, "clz32({a})"),
            O::I32Ctz => self.un(T::I, "ctz32({a})"),
            O::I32Popcnt => self.un(T::I, "(u32)__builtin_popcount({a})"),
            O::I32Add => self.bin(T::I, "{a} + {b}"),
            O::I32Sub => self.bin(T::I, "{a} - {b}"),
            O::I32Mul => self.bin(T::I, "{a} * {b}"),
            O::I32DivS => self.bin(T::I, "div_s32(I, {a}, {b})"),
            O::I32DivU => self.bin(T::I, "div_u32(I, {a}, {b})"),
            O::I32RemS => self.bin(T::I, "rem_s32(I, {a}, {b})"),
            O::I32RemU => self.bin(T::I, "rem_u32(I, {a}, {b})"),
            O::I32And => self.bin(T::I, "{a} & {b}"),
            O::I32Or => self.bin(T::I, "{a} | {b}"),
            O::I32Xor => self.bin(T::I, "{a} ^ {b}"),
            O::I32Shl => self.bin(T::I, "{a} << ({b} & 31)"),
            O::I32ShrS => self.bin(T::I, "(u32)((i32){a} >> ({b} & 31))"),
            O::I32ShrU => self.bin(T::I, "{a} >> ({b} & 31)"),
            O::I32Rotl => self.bin(T::I, "rotl32({a}, {b})"),
            O::I32Rotr => self.bin(T::I, "rotr32({a}, {b})"),
            // i64
            O::I64Eqz => self.un(T::I, "{a} == 0"),
            O::I64Eq => self.bin(T::I, "{a} == {b}"),
            O::I64Ne => self.bin(T::I, "{a} != {b}"),
            O::I64LtS => self.bin(T::I, "(i64){a} < (i64){b}"),
            O::I64LtU => self.bin(T::I, "{a} < {b}"),
            O::I64GtS => self.bin(T::I, "(i64){a} > (i64){b}"),
            O::I64GtU => self.bin(T::I, "{a} > {b}"),
            O::I64LeS => self.bin(T::I, "(i64){a} <= (i64){b}"),
            O::I64LeU => self.bin(T::I, "{a} <= {b}"),
            O::I64GeS => self.bin(T::I, "(i64){a} >= (i64){b}"),
            O::I64GeU => self.bin(T::I, "{a} >= {b}"),
            O::I64Clz => self.un(T::J, "clz64({a})"),
            O::I64Ctz => self.un(T::J, "ctz64({a})"),
            O::I64Popcnt => self.un(T::J, "(u64)__builtin_popcountll({a})"),
            O::I64Add => self.bin(T::J, "{a} + {b}"),
            O::I64Sub => self.bin(T::J, "{a} - {b}"),
            O::I64Mul => self.bin(T::J, "{a} * {b}"),
            O::I64DivS => self.bin(T::J, "div_s64(I, {a}, {b})"),
            O::I64DivU => self.bin(T::J, "div_u64(I, {a}, {b})"),
            O::I64RemS => self.bin(T::J, "rem_s64(I, {a}, {b})"),
            O::I64RemU => self.bin(T::J, "rem_u64(I, {a}, {b})"),
            O::I64And => self.bin(T::J, "{a} & {b}"),
            O::I64Or => self.bin(T::J, "{a} | {b}"),
            O::I64Xor => self.bin(T::J, "{a} ^ {b}"),
            O::I64Shl => self.bin(T::J, "{a} << ({b} & 63)"),
            O::I64ShrS => self.bin(T::J, "(u64)((i64){a} >> ({b} & 63))"),
            O::I64ShrU => self.bin(T::J, "{a} >> ({b} & 63)"),
            O::I64Rotl => self.bin(T::J, "rotl64({a}, {b})"),
            O::I64Rotr => self.bin(T::J, "rotr64({a}, {b})"),
            // f32
            O::F32Eq => self.bin(T::I, "{a} == {b}"),
            O::F32Ne => self.bin(T::I, "{a} != {b}"),
            O::F32Lt => self.bin(T::I, "{a} < {b}"),
            O::F32Gt => self.bin(T::I, "{a} > {b}"),
            O::F32Le => self.bin(T::I, "{a} <= {b}"),
            O::F32Ge => self.bin(T::I, "{a} >= {b}"),
            O::F64Eq => self.bin(T::I, "{a} == {b}"),
            O::F64Ne => self.bin(T::I, "{a} != {b}"),
            O::F64Lt => self.bin(T::I, "{a} < {b}"),
            O::F64Gt => self.bin(T::I, "{a} > {b}"),
            O::F64Le => self.bin(T::I, "{a} <= {b}"),
            O::F64Ge => self.bin(T::I, "{a} >= {b}"),
            O::F32Abs => self.un(T::F, "fabs32({a})"),
            O::F32Neg => self.un(T::F, "fneg32({a})"),
            O::F32Ceil => self.un(T::F, "__builtin_ceilf({a})"),
            O::F32Floor => self.un(T::F, "__builtin_floorf({a})"),
            O::F32Trunc => self.un(T::F, "__builtin_truncf({a})"),
            O::F32Nearest => self.un(T::F, "__builtin_roundevenf({a})"),
            O::F32Sqrt => self.un(T::F, "__builtin_sqrtf({a})"),
            O::F32Add => self.bin(T::F, "{a} + {b}"),
            O::F32Sub => self.bin(T::F, "{a} - {b}"),
            O::F32Mul => self.bin(T::F, "{a} * {b}"),
            O::F32Div => self.bin(T::F, "{a} / {b}"),
            O::F32Min => self.bin(T::F, "fmin32({a}, {b})"),
            O::F32Max => self.bin(T::F, "fmax32({a}, {b})"),
            O::F32Copysign => self.bin(T::F, "fcopysign32({a}, {b})"),
            O::F64Abs => self.un(T::D, "fabs64({a})"),
            O::F64Neg => self.un(T::D, "fneg64({a})"),
            O::F64Ceil => self.un(T::D, "__builtin_ceil({a})"),
            O::F64Floor => self.un(T::D, "__builtin_floor({a})"),
            O::F64Trunc => self.un(T::D, "__builtin_trunc({a})"),
            O::F64Nearest => self.un(T::D, "__builtin_roundeven({a})"),
            O::F64Sqrt => self.un(T::D, "__builtin_sqrt({a})"),
            O::F64Add => self.bin(T::D, "{a} + {b}"),
            O::F64Sub => self.bin(T::D, "{a} - {b}"),
            O::F64Mul => self.bin(T::D, "{a} * {b}"),
            O::F64Div => self.bin(T::D, "{a} / {b}"),
            O::F64Min => self.bin(T::D, "fmin64({a}, {b})"),
            O::F64Max => self.bin(T::D, "fmax64({a}, {b})"),
            O::F64Copysign => self.bin(T::D, "fcopysign64({a}, {b})"),
            // conversions
            O::I32WrapI64 => self.un(T::I, "(u32){a}"),
            O::I32TruncF32S => self.un(T::I, "(u32)trunc_f32_i32s(I, {a})"),
            O::I32TruncF32U => self.un(T::I, "trunc_f32_i32u(I, {a})"),
            O::I32TruncF64S => self.un(T::I, "(u32)trunc_f64_i32s(I, {a})"),
            O::I32TruncF64U => self.un(T::I, "trunc_f64_i32u(I, {a})"),
            O::I64ExtendI32S => self.un(T::J, "(u64)(i64)(i32){a}"),
            O::I64ExtendI32U => self.un(T::J, "(u64){a}"),
            O::I64TruncF32S => self.un(T::J, "(u64)trunc_f32_i64s(I, {a})"),
            O::I64TruncF32U => self.un(T::J, "trunc_f32_i64u(I, {a})"),
            O::I64TruncF64S => self.un(T::J, "(u64)trunc_f64_i64s(I, {a})"),
            O::I64TruncF64U => self.un(T::J, "trunc_f64_i64u(I, {a})"),
            O::F32ConvertI32S => self.un(T::F, "(f32)(i32){a}"),
            O::F32ConvertI32U => self.un(T::F, "(f32){a}"),
            O::F32ConvertI64S => self.un(T::F, "(f32)(i64){a}"),
            O::F32ConvertI64U => self.un(T::F, "(f32){a}"),
            O::F32DemoteF64 => self.un(T::F, "(f32){a}"),
            O::F64ConvertI32S => self.un(T::D, "(f64)(i32){a}"),
            O::F64ConvertI32U => self.un(T::D, "(f64){a}"),
            O::F64ConvertI64S => self.un(T::D, "(f64)(i64){a}"),
            O::F64ConvertI64U => self.un(T::D, "(f64){a}"),
            O::F64PromoteF32 => self.un(T::D, "(f64){a}"),
            O::I32ReinterpretF32 => self.un(T::I, "bits_f32({a})"),
            O::I64ReinterpretF64 => self.un(T::J, "bits_f64({a})"),
            O::F32ReinterpretI32 => self.un(T::F, "f32_bits({a})"),
            O::F64ReinterpretI64 => self.un(T::D, "f64_bits({a})"),
            O::I32Extend8S => self.un(T::I, "(u32)(i32)(i8){a}"),
            O::I32Extend16S => self.un(T::I, "(u32)(i32)(i16){a}"),
            O::I64Extend8S => self.un(T::J, "(u64)(i64)(i8){a}"),
            O::I64Extend16S => self.un(T::J, "(u64)(i64)(i16){a}"),
            O::I64Extend32S => self.un(T::J, "(u64)(i64)(i32){a}"),
            O::I32TruncSatF32S => self.un(T::I, "(u32)sat_f32_i32s({a})"),
            O::I32TruncSatF32U => self.un(T::I, "sat_f32_i32u({a})"),
            O::I32TruncSatF64S => self.un(T::I, "(u32)sat_f64_i32s({a})"),
            O::I32TruncSatF64U => self.un(T::I, "sat_f64_i32u({a})"),
            O::I64TruncSatF32S => self.un(T::J, "(u64)sat_f32_i64s({a})"),
            O::I64TruncSatF32U => self.un(T::J, "sat_f32_i64u({a})"),
            O::I64TruncSatF64S => self.un(T::J, "(u64)sat_f64_i64s({a})"),
            O::I64TruncSatF64U => self.un(T::J, "sat_f64_i64u({a})"),

            // SIMD memory
            O::V128Load { memarg } => self.vload("v_load", memarg)?,
            O::V128Load8x8S { memarg } => self.vload("v_load8x8_s", memarg)?,
            O::V128Load8x8U { memarg } => self.vload("v_load8x8_u", memarg)?,
            O::V128Load16x4S { memarg } => self.vload("v_load16x4_s", memarg)?,
            O::V128Load16x4U { memarg } => self.vload("v_load16x4_u", memarg)?,
            O::V128Load32x2S { memarg } => self.vload("v_load32x2_s", memarg)?,
            O::V128Load32x2U { memarg } => self.vload("v_load32x2_u", memarg)?,
            O::V128Load8Splat { memarg } => self.vload("v_load8_splat", memarg)?,
            O::V128Load16Splat { memarg } => self.vload("v_load16_splat", memarg)?,
            O::V128Load32Splat { memarg } => self.vload("v_load32_splat", memarg)?,
            O::V128Load64Splat { memarg } => self.vload("v_load64_splat", memarg)?,
            O::V128Load32Zero { memarg } => self.vload("v_load32_zero", memarg)?,
            O::V128Load64Zero { memarg } => self.vload("v_load64_zero", memarg)?,
            O::V128Store { memarg } => {
                let v = self.pop();
                let a = self.pop();
                let p = self.addr(&a, memarg.offset);
                self.line(&format!("v_store({p}, {v});"));
            }
            O::V128Load8Lane { memarg, lane } | O::V128Load16Lane { memarg, lane } | O::V128Load32Lane { memarg, lane } | O::V128Load64Lane { memarg, lane } => {
                let w = match op {
                    O::V128Load8Lane { .. } => 8,
                    O::V128Load16Lane { .. } => 16,
                    O::V128Load32Lane { .. } => 32,
                    _ => 64,
                };
                let v = self.pop();
                let a = self.pop();
                let d = self.push(T::V);
                let p = self.addr(&a, memarg.offset);
                self.line(&format!("{d} = v_load{w}_lane({p}, {v}, {lane});"));
            }
            O::V128Store8Lane { memarg, lane } | O::V128Store16Lane { memarg, lane } | O::V128Store32Lane { memarg, lane } | O::V128Store64Lane { memarg, lane } => {
                let w = match op {
                    O::V128Store8Lane { .. } => 8,
                    O::V128Store16Lane { .. } => 16,
                    O::V128Store32Lane { .. } => 32,
                    _ => 64,
                };
                let v = self.pop();
                let a = self.pop();
                let p = self.addr(&a, memarg.offset);
                self.line(&format!("v_store{w}_lane({p}, {v}, {lane});"));
            }
            // SIMD lanes
            O::I8x16Shuffle { lanes } => {
                let l: Vec<String> = lanes.iter().map(|x| x.to_string()).collect();
                self.bin(T::V, &format!("(v128)__builtin_shufflevector((u8x16){{a}}, (u8x16){{b}}, {})", l.join(", ")));
            }
            O::I8x16ExtractLaneS { lane } => self.un(T::I, &format!("(u32)(i32)((i8x16){{a}})[{lane}]")),
            O::I8x16ExtractLaneU { lane } => self.un(T::I, &format!("(u32)((u8x16){{a}})[{lane}]")),
            O::I16x8ExtractLaneS { lane } => self.un(T::I, &format!("(u32)(i32)((i16x8){{a}})[{lane}]")),
            O::I16x8ExtractLaneU { lane } => self.un(T::I, &format!("(u32)((u16x8){{a}})[{lane}]")),
            O::I32x4ExtractLane { lane } => self.un(T::I, &format!("((u32x4){{a}})[{lane}]")),
            O::I64x2ExtractLane { lane } => self.un(T::J, &format!("((u64x2){{a}})[{lane}]")),
            O::F32x4ExtractLane { lane } => self.un(T::F, &format!("((f32x4){{a}})[{lane}]")),
            O::F64x2ExtractLane { lane } => self.un(T::D, &format!("((f64x2){{a}})[{lane}]")),
            O::I8x16ReplaceLane { lane } => self.replace("u8x16", "u8", *lane),
            O::I16x8ReplaceLane { lane } => self.replace("u16x8", "u16", *lane),
            O::I32x4ReplaceLane { lane } => self.replace("u32x4", "u32", *lane),
            O::I64x2ReplaceLane { lane } => self.replace("u64x2", "u64", *lane),
            O::F32x4ReplaceLane { lane } => self.replace("f32x4", "f32", *lane),
            O::F64x2ReplaceLane { lane } => self.replace("f64x2", "f64", *lane),
            O::I8x16Splat => self.un(T::V, "i8x16_splat((u8){a})"),
            O::I16x8Splat => self.un(T::V, "i16x8_splat((u16){a})"),
            O::I32x4Splat => self.un(T::V, "i32x4_splat({a})"),
            O::I64x2Splat => self.un(T::V, "i64x2_splat({a})"),
            O::F32x4Splat => self.un(T::V, "f32x4_splat({a})"),
            O::F64x2Splat => self.un(T::V, "f64x2_splat({a})"),
            O::V128AnyTrue => self.un(T::I, "v_any_true({a})"),
            O::V128Bitselect => {
                let c = self.pop();
                let b = self.pop();
                let a = self.pop();
                let d = self.push(T::V);
                self.line(&format!("{d} = v128_bitselect({a}, {b}, {c});"));
            }
            O::I8x16Shl | O::I8x16ShrS | O::I8x16ShrU | O::I16x8Shl | O::I16x8ShrS | O::I16x8ShrU | O::I32x4Shl | O::I32x4ShrS | O::I32x4ShrU | O::I64x2Shl | O::I64x2ShrS | O::I64x2ShrU => {
                let name = simd_name(op).unwrap();
                let s = self.pop();
                let a = self.pop();
                let d = self.push(T::V);
                self.line(&format!("{d} = {name}({a}, (u32){s});"));
            }
            _ => {
                if let Some((name, arity, res)) = simd_simple(op) {
                    if arity == 2 {
                        self.bin(res, &format!("{name}({{a}}, {{b}})"));
                    } else {
                        self.un(res, &format!("{name}({{a}})"));
                    }
                } else {
                    bail!("unsupported operator {op:?}");
                }
            }
        }
        Ok(())
    }

    fn replace(&mut self, vt: &str, st: &str, lane: u8) {
        let s = self.pop();
        let v = self.pop();
        let d = self.push(T::V);
        self.line(&format!("{{ {vt} _t = ({vt}){v}; _t[{lane}] = ({st}){s}; {d} = (v128)_t; }}"));
    }

    fn else_entry(&mut self, id: u32, base: usize, params: &[T], saved: &[String]) {
        self.line(&format!("E{id}:;"));
        for (k, &t) in params.iter().enumerate() {
            let dst = self.slot(base + k, t);
            let line = format!("{dst} = {};", saved[k]);
            self.line(&line);
        }
        self.stack.truncate(base);
        self.stack.extend_from_slice(params);
        let f = self.ctrl.last_mut().unwrap();
        self.reachable = f.head_reachable;
    }

    fn end_frame(&mut self) -> Result<()> {
        let f = self.ctrl.pop().unwrap();
        match f.kind {
            K::Func => {
                // the function's exit block: save the fuel variable and return
                self.line("Lret:;");
                self.save();
                match self.ret {
                    Some(t) => {
                        let v = self.slot(0, t);
                        self.line(&format!("return {v};"));
                    }
                    None => self.line("return;"),
                }
            }
            K::If if f.cons_end.is_none() => {
                self.line(&format!("E{}:;", f.id));
                self.line(&format!("L{}:;", f.id));
            }
            _ => self.line(&format!("L{}:;", f.id)),
        }
        self.stack.truncate(f.base);
        self.stack.extend_from_slice(&f.results);
        Ok(())
    }

    /// wasmtime's translate_unreachable_operator.
    fn unreachable_op(&mut self, op: &Operator) -> Result<()> {
        use Operator as O;
        match op {
            O::If { .. } | O::Loop { .. } | O::Block { .. } | O::TryTable { .. } => {
                let id = self.label();
                let base = self.stack.len();
                let kind = if matches!(op, O::If { .. }) { K::If } else { K::Block };
                self.ctrl.push(Frame { kind, id, base, params: vec![], results: vec![], branched: false, dead: true, head_reachable: false, cons_end: None, saved: vec![] });
            }
            O::Else => {
                let f = self.ctrl.last_mut().unwrap();
                f.cons_end = Some(false);
                if f.head_reachable && !f.dead {
                    let (id, base, params, saved) = (f.id, f.base, f.params.clone(), f.saved.clone());
                    self.else_entry(id, base, &params, &saved);
                }
            }
            O::End => {
                let f = self.ctrl.last().unwrap();
                let anyway = match (f.kind, f.cons_end) {
                    (K::Loop, _) => false,
                    (K::If, None) => f.head_reachable,
                    (K::If, Some(c)) => f.head_reachable && c,
                    _ => false,
                };
                if !f.dead && (f.branched || anyway) {
                    self.reachable = true;
                    self.end_frame()?;
                } else {
                    let f = self.ctrl.pop().unwrap();
                    self.stack.truncate(f.base.min(self.stack.len()));
                    if f.kind == K::Func {
                        // unreachable function end: nothing returns here
                    }
                }
            }
            _ => {}
        }
        Ok(())
    }

    fn local_t(&self, i: u32) -> T {
        self.locals[i as usize]
    }
}

/// Lane-wise SIMD operators that map onto one helper in aot_rt.h: (helper, arity, result type).
fn simd_simple(op: &Operator) -> Option<(&'static str, u8, T)> {
    let name = simd_name(op)?;
    use Operator as O;
    let r = match op {
        O::V128AnyTrue
        | O::I8x16AllTrue
        | O::I16x8AllTrue
        | O::I32x4AllTrue
        | O::I64x2AllTrue
        | O::I8x16Bitmask
        | O::I16x8Bitmask
        | O::I32x4Bitmask
        | O::I64x2Bitmask => (1, T::I),
        O::V128Not
        | O::I8x16Abs
        | O::I8x16Neg
        | O::I8x16Popcnt
        | O::I16x8Abs
        | O::I16x8Neg
        | O::I32x4Abs
        | O::I32x4Neg
        | O::I64x2Abs
        | O::I64x2Neg
        | O::I16x8ExtendLowI8x16S
        | O::I16x8ExtendHighI8x16S
        | O::I16x8ExtendLowI8x16U
        | O::I16x8ExtendHighI8x16U
        | O::I32x4ExtendLowI16x8S
        | O::I32x4ExtendHighI16x8S
        | O::I32x4ExtendLowI16x8U
        | O::I32x4ExtendHighI16x8U
        | O::I64x2ExtendLowI32x4S
        | O::I64x2ExtendHighI32x4S
        | O::I64x2ExtendLowI32x4U
        | O::I64x2ExtendHighI32x4U
        | O::I16x8ExtAddPairwiseI8x16S
        | O::I16x8ExtAddPairwiseI8x16U
        | O::I32x4ExtAddPairwiseI16x8S
        | O::I32x4ExtAddPairwiseI16x8U
        | O::F32x4Ceil
        | O::F32x4Floor
        | O::F32x4Trunc
        | O::F32x4Nearest
        | O::F32x4Abs
        | O::F32x4Neg
        | O::F32x4Sqrt
        | O::F64x2Ceil
        | O::F64x2Floor
        | O::F64x2Trunc
        | O::F64x2Nearest
        | O::F64x2Abs
        | O::F64x2Neg
        | O::F64x2Sqrt
        | O::I32x4TruncSatF32x4S
        | O::I32x4TruncSatF32x4U
        | O::F32x4ConvertI32x4S
        | O::F32x4ConvertI32x4U
        | O::I32x4TruncSatF64x2SZero
        | O::I32x4TruncSatF64x2UZero
        | O::F64x2ConvertLowI32x4S
        | O::F64x2ConvertLowI32x4U
        | O::F32x4DemoteF64x2Zero
        | O::F64x2PromoteLowF32x4 => (1, T::V),
        _ => (2, T::V),
    };
    Some((name, r.0, r.1))
}

fn simd_name(op: &Operator) -> Option<&'static str> {
    use Operator as O;
    Some(match op {
        O::V128AnyTrue => "v_any_true",
        O::V128Not => "v128_not",
        O::V128And => "v128_and",
        O::V128AndNot => "v128_andnot",
        O::V128Or => "v128_or",
        O::V128Xor => "v128_xor",
        O::I8x16Swizzle => "i8x16_swizzle",
        O::I8x16AllTrue => "i8x16_all_true",
        O::I16x8AllTrue => "i16x8_all_true",
        O::I32x4AllTrue => "i32x4_all_true",
        O::I64x2AllTrue => "i64x2_all_true",
        O::I8x16Bitmask => "i8x16_bitmask",
        O::I16x8Bitmask => "i16x8_bitmask",
        O::I32x4Bitmask => "i32x4_bitmask",
        O::I64x2Bitmask => "i64x2_bitmask",
        O::I8x16Eq => "i8x16_eq",
        O::I8x16Ne => "i8x16_ne",
        O::I8x16LtS => "i8x16_lt_s",
        O::I8x16LtU => "i8x16_lt_u",
        O::I8x16GtS => "i8x16_gt_s",
        O::I8x16GtU => "i8x16_gt_u",
        O::I8x16LeS => "i8x16_le_s",
        O::I8x16LeU => "i8x16_le_u",
        O::I8x16GeS => "i8x16_ge_s",
        O::I8x16GeU => "i8x16_ge_u",
        O::I16x8Eq => "i16x8_eq",
        O::I16x8Ne => "i16x8_ne",
        O::I16x8LtS => "i16x8_lt_s",
        O::I16x8LtU => "i16x8_lt_u",
        O::I16x8GtS => "i16x8_gt_s",
        O::I16x8GtU => "i16x8_gt_u",
        O::I16x8LeS => "i16x8_le_s",
        O::I16x8LeU => "i16x8_le_u",
        O::I16x8GeS => "i16x8_ge_s",
        O::I16x8GeU => "i16x8_ge_u",
        O::I32x4Eq => "i32x4_eq",
        O::I32x4Ne => "i32x4_ne",
        O::I32x4LtS => "i32x4_lt_s",
        O::I32x4LtU => "i32x4_lt_u",
        O::I32x4GtS => "i32x4_gt_s",
        O::I32x4GtU => "i32x4_gt_u",
        O::I32x4LeS => "i32x4_le_s",
        O::I32x4LeU => "i32x4_le_u",
        O::I32x4GeS => "i32x4_ge_s",
        O::I32x4GeU => "i32x4_ge_u",
        O::I64x2Eq => "i64x2_eq",
        O::I64x2Ne => "i64x2_ne",
        O::I64x2LtS => "i64x2_lt_s",
        O::I64x2GtS => "i64x2_gt_s",
        O::I64x2LeS => "i64x2_le_s",
        O::I64x2GeS => "i64x2_ge_s",
        O::F32x4Eq => "f32x4_eq",
        O::F32x4Ne => "f32x4_ne",
        O::F32x4Lt => "f32x4_lt",
        O::F32x4Gt => "f32x4_gt",
        O::F32x4Le => "f32x4_le",
        O::F32x4Ge => "f32x4_ge",
        O::F64x2Eq => "f64x2_eq",
        O::F64x2Ne => "f64x2_ne",
        O::F64x2Lt => "f64x2_lt",
        O::F64x2Gt => "f64x2_gt",
        O::F64x2Le => "f64x2_le",
        O::F64x2Ge => "f64x2_ge",
        O::I8x16Abs => "i8x16_abs",
        O::I8x16Neg => "i8x16_neg",
        O::I8x16Popcnt => "i8x16_popcnt",
        O::I8x16NarrowI16x8S => "i8x16_narrow_i16x8_s",
        O::I8x16NarrowI16x8U => "i8x16_narrow_i16x8_u",
        O::I8x16Shl => "i8x16_shl",
        O::I8x16ShrS => "i8x16_shr_s",
        O::I8x16ShrU => "i8x16_shr_u",
        O::I8x16Add => "i8x16_add",
        O::I8x16AddSatS => "i8x16_add_sat_s",
        O::I8x16AddSatU => "i8x16_add_sat_u",
        O::I8x16Sub => "i8x16_sub",
        O::I8x16SubSatS => "i8x16_sub_sat_s",
        O::I8x16SubSatU => "i8x16_sub_sat_u",
        O::I8x16MinS => "i8x16_min_s",
        O::I8x16MinU => "i8x16_min_u",
        O::I8x16MaxS => "i8x16_max_s",
        O::I8x16MaxU => "i8x16_max_u",
        O::I8x16AvgrU => "i8x16_avgr_u",
        O::I16x8ExtAddPairwiseI8x16S => "i16x8_extadd_pairwise_i8x16_s",
        O::I16x8ExtAddPairwiseI8x16U => "i16x8_extadd_pairwise_i8x16_u",
        O::I16x8Abs => "i16x8_abs",
        O::I16x8Neg => "i16x8_neg",
        O::I16x8Q15MulrSatS => "i16x8_q15mulr_sat_s",
        O::I16x8NarrowI32x4S => "i16x8_narrow_i32x4_s",
        O::I16x8NarrowI32x4U => "i16x8_narrow_i32x4_u",
        O::I16x8ExtendLowI8x16S => "i16x8_extend_low_i8x16_s",
        O::I16x8ExtendHighI8x16S => "i16x8_extend_high_i8x16_s",
        O::I16x8ExtendLowI8x16U => "i16x8_extend_low_i8x16_u",
        O::I16x8ExtendHighI8x16U => "i16x8_extend_high_i8x16_u",
        O::I16x8Shl => "i16x8_shl",
        O::I16x8ShrS => "i16x8_shr_s",
        O::I16x8ShrU => "i16x8_shr_u",
        O::I16x8Add => "i16x8_add",
        O::I16x8AddSatS => "i16x8_add_sat_s",
        O::I16x8AddSatU => "i16x8_add_sat_u",
        O::I16x8Sub => "i16x8_sub",
        O::I16x8SubSatS => "i16x8_sub_sat_s",
        O::I16x8SubSatU => "i16x8_sub_sat_u",
        O::I16x8Mul => "i16x8_mul",
        O::I16x8MinS => "i16x8_min_s",
        O::I16x8MinU => "i16x8_min_u",
        O::I16x8MaxS => "i16x8_max_s",
        O::I16x8MaxU => "i16x8_max_u",
        O::I16x8AvgrU => "i16x8_avgr_u",
        O::I16x8ExtMulLowI8x16S => "i16x8_extmul_low_i8x16_s",
        O::I16x8ExtMulHighI8x16S => "i16x8_extmul_high_i8x16_s",
        O::I16x8ExtMulLowI8x16U => "i16x8_extmul_low_i8x16_u",
        O::I16x8ExtMulHighI8x16U => "i16x8_extmul_high_i8x16_u",
        O::I32x4ExtAddPairwiseI16x8S => "i32x4_extadd_pairwise_i16x8_s",
        O::I32x4ExtAddPairwiseI16x8U => "i32x4_extadd_pairwise_i16x8_u",
        O::I32x4Abs => "i32x4_abs",
        O::I32x4Neg => "i32x4_neg",
        O::I32x4ExtendLowI16x8S => "i32x4_extend_low_i16x8_s",
        O::I32x4ExtendHighI16x8S => "i32x4_extend_high_i16x8_s",
        O::I32x4ExtendLowI16x8U => "i32x4_extend_low_i16x8_u",
        O::I32x4ExtendHighI16x8U => "i32x4_extend_high_i16x8_u",
        O::I32x4Shl => "i32x4_shl",
        O::I32x4ShrS => "i32x4_shr_s",
        O::I32x4ShrU => "i32x4_shr_u",
        O::I32x4Add => "i32x4_add",
        O::I32x4Sub => "i32x4_sub",
        O::I32x4Mul => "i32x4_mul",
        O::I32x4MinS => "i32x4_min_s",
        O::I32x4MinU => "i32x4_min_u",
        O::I32x4MaxS => "i32x4_max_s",
        O::I32x4MaxU => "i32x4_max_u",
        O::I32x4DotI16x8S => "i32x4_dot_i16x8_s",
        O::I32x4ExtMulLowI16x8S => "i32x4_extmul_low_i16x8_s",
        O::I32x4ExtMulHighI16x8S => "i32x4_extmul_high_i16x8_s",
        O::I32x4ExtMulLowI16x8U => "i32x4_extmul_low_i16x8_u",
        O::I32x4ExtMulHighI16x8U => "i32x4_extmul_high_i16x8_u",
        O::I64x2Abs => "i64x2_abs",
        O::I64x2Neg => "i64x2_neg",
        O::I64x2ExtendLowI32x4S => "i64x2_extend_low_i32x4_s",
        O::I64x2ExtendHighI32x4S => "i64x2_extend_high_i32x4_s",
        O::I64x2ExtendLowI32x4U => "i64x2_extend_low_i32x4_u",
        O::I64x2ExtendHighI32x4U => "i64x2_extend_high_i32x4_u",
        O::I64x2Shl => "i64x2_shl",
        O::I64x2ShrS => "i64x2_shr_s",
        O::I64x2ShrU => "i64x2_shr_u",
        O::I64x2Add => "i64x2_add",
        O::I64x2Sub => "i64x2_sub",
        O::I64x2Mul => "i64x2_mul",
        O::I64x2ExtMulLowI32x4S => "i64x2_extmul_low_i32x4_s",
        O::I64x2ExtMulHighI32x4S => "i64x2_extmul_high_i32x4_s",
        O::I64x2ExtMulLowI32x4U => "i64x2_extmul_low_i32x4_u",
        O::I64x2ExtMulHighI32x4U => "i64x2_extmul_high_i32x4_u",
        O::F32x4Ceil => "f32x4_ceil",
        O::F32x4Floor => "f32x4_floor",
        O::F32x4Trunc => "f32x4_trunc",
        O::F32x4Nearest => "f32x4_nearest",
        O::F32x4Abs => "f32x4_abs",
        O::F32x4Neg => "f32x4_neg",
        O::F32x4Sqrt => "f32x4_sqrt",
        O::F32x4Add => "f32x4_add",
        O::F32x4Sub => "f32x4_sub",
        O::F32x4Mul => "f32x4_mul",
        O::F32x4Div => "f32x4_div",
        O::F32x4Min => "f32x4_min",
        O::F32x4Max => "f32x4_max",
        O::F32x4PMin => "f32x4_pmin",
        O::F32x4PMax => "f32x4_pmax",
        O::F64x2Ceil => "f64x2_ceil",
        O::F64x2Floor => "f64x2_floor",
        O::F64x2Trunc => "f64x2_trunc",
        O::F64x2Nearest => "f64x2_nearest",
        O::F64x2Abs => "f64x2_abs",
        O::F64x2Neg => "f64x2_neg",
        O::F64x2Sqrt => "f64x2_sqrt",
        O::F64x2Add => "f64x2_add",
        O::F64x2Sub => "f64x2_sub",
        O::F64x2Mul => "f64x2_mul",
        O::F64x2Div => "f64x2_div",
        O::F64x2Min => "f64x2_min",
        O::F64x2Max => "f64x2_max",
        O::F64x2PMin => "f64x2_pmin",
        O::F64x2PMax => "f64x2_pmax",
        O::I32x4TruncSatF32x4S => "i32x4_trunc_sat_f32x4_s",
        O::I32x4TruncSatF32x4U => "i32x4_trunc_sat_f32x4_u",
        O::F32x4ConvertI32x4S => "f32x4_convert_i32x4_s",
        O::F32x4ConvertI32x4U => "f32x4_convert_i32x4_u",
        O::I32x4TruncSatF64x2SZero => "i32x4_trunc_sat_f64x2_s_zero",
        O::I32x4TruncSatF64x2UZero => "i32x4_trunc_sat_f64x2_u_zero",
        O::F64x2ConvertLowI32x4S => "f64x2_convert_low_i32x4_s",
        O::F64x2ConvertLowI32x4U => "f64x2_convert_low_i32x4_u",
        O::F32x4DemoteF64x2Zero => "f32x4_demote_f64x2_zero",
        O::F64x2PromoteLowF32x4 => "f64x2_promote_low_f32x4",
        _ => return None,
    })
}

fn sig_string(s: &Sig) -> String {
    let r: String = s.results.iter().map(|t| t.ch()).collect();
    let p: String = s.params.iter().map(|t| t.ch()).collect();
    format!("{r}:{p}")
}

fn c_str(s: &str) -> String {
    let mut o = String::from("\"");
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || b == b'_' || b == b'.' || b == b'-' {
            o.push(b as char);
        } else {
            write!(o, "\\x{b:02x}\"\"").unwrap();
        }
    }
    o.push('"');
    o
}

fn gen_function(m: &Module, bulk: &BulkLog, f: usize, body: &wasmparser::FunctionBody) -> Result<String> {
    let sig = m.types[m.funcs[f] as usize].clone().unwrap();
    let mut locals: Vec<T> = sig.params.clone();
    let mut lr = body.get_locals_reader()?;
    for _ in 0..lr.get_count() {
        let (n, t) = lr.read()?;
        for _ in 0..n {
            locals.push(T::of(t));
        }
    }
    let mut fx = Fx {
        m,
        bulk,
        body: String::new(),
        decls: BTreeSet::new(),
        extra: vec![],
        stack: vec![],
        ctrl: vec![],
        reachable: true,
        pend: 0,
        next: 0,
        handlers: vec![],
        uses_hp: false,
        ret: sig.results.first().copied(),
        locals: locals.clone(),
        fid: f,
        last_load: None,
    };
    fx.ctrl.push(Frame { kind: K::Func, id: 0, base: 0, params: vec![], results: sig.results.clone(), branched: false, dead: false, head_reachable: true, cons_end: None, saved: vec![] });
    // wasmtime starts every function with 1 fuel consumed, flushed by the entry check.
    fx.pend = 1;
    fx.check();
    let mut r = body.get_operators_reader()?;
    while !r.eof() {
        let (op, off) = r.read_with_offset()?;
        fx.op(&op, off as u32).with_context(|| format!("function {f} at offset {off}"))?;
    }
    let ret = fx.ret.map_or("void", |t| t.c());
    let mut s = String::new();
    let mut params = vec!["Inst* I".to_string()];
    for (k, t) in sig.params.iter().enumerate() {
        params.push(format!("{} l{k}", t.c()));
    }
    writeln!(s, "HIDDEN {ret} wf{f}({}) {{", params.join(", ")).unwrap();
    s.push_str("  u8* const M = I->mem; i64 fuel;\n");
    for (k, t) in locals.iter().enumerate().skip(sig.params.len()) {
        writeln!(s, "  {} l{k} = {};", t.c(), t.zero()).unwrap();
    }
    for (d, t) in &fx.decls {
        writeln!(s, "  {} s{d}{};", t.c(), t.ch()).unwrap();
    }
    for e in &fx.extra {
        writeln!(s, "  {e}").unwrap();
    }
    s.push_str("  (void)M;\n  fuel = I->fuel;\n");
    s.push_str(&fx.body);
    if fx.uses_hp {
        match fx.ret {
            Some(t) => writeln!(s, "HP: return {};", t.zero()).unwrap(),
            None => s.push_str("HP: return;\n"),
        }
    }
    for h in &fx.handlers {
        s.push_str(h);
    }
    s.push_str("}\n");
    Ok(s)
}

/// Translates a module; `bulk` is the vendored Cranelift's record of its bulk-memory fuel decisions.
pub fn translate(wasm: &[u8], bulk: &BulkLog, units: usize) -> Result<CModule> {
    let m = parse(wasm)?;
    let tbl_n = m.table.unwrap_or(0);
    let mut h = String::new();
    h.push_str(include_str!("aot_rt.h"));
    h.push_str("typedef struct { void* f; u32 sig; } TE;\n");
    writeln!(h, "#define TBL_N {tbl_n}u").unwrap();
    h.push_str("extern HIDDEN const TE TBL[];\nextern HIDDEN void* IMPS[];\nextern u64 fr_site;\n");
    for f in m.nimp..m.funcs.len() {
        let sig = m.types[m.funcs[f] as usize].as_ref().unwrap();
        let mut p = vec!["Inst*".to_string()];
        p.extend(sig.params.iter().map(|t| t.c().to_string()));
        writeln!(h, "HIDDEN {} wf{f}({});", sig.results.first().map_or("void", |t| t.c()), p.join(", ")).unwrap();
    }

    // descriptor unit
    let mut d = String::from("#include \"mod.h\"\n");
    writeln!(d, "HIDDEN void* IMPS[{}];", m.nimp.max(1)).unwrap();
    let mut table: Vec<Option<u32>> = vec![None; tbl_n as usize];
    for (off, items) in &m.elems {
        for (k, &f) in items.iter().enumerate() {
            let i = *off as usize + k;
            if i >= table.len() {
                bail!("element segment out of the table");
            }
            table[i] = Some(f);
        }
    }
    writeln!(d, "HIDDEN const TE TBL[{}] = {{", tbl_n.max(1)).unwrap();
    for (i, e) in table.iter().enumerate() {
        if let Some(f) = e {
            let f = *f as usize;
            if f < m.nimp {
                bail!("imported function in the table");
            }
            writeln!(d, "  [{i}] = {{ (void*)wf{f}, {}u }},", m.canon[m.funcs[f] as usize]).unwrap();
        }
    }
    d.push_str("};\n");
    for (k, (_, bytes)) in m.data.iter().enumerate() {
        write!(d, "static const u8 D{k}[{}] = {{", bytes.len().max(1)).unwrap();
        for (i, b) in bytes.iter().enumerate() {
            if i % 32 == 0 {
                d.push('\n');
            }
            write!(d, "{b},").unwrap();
        }
        d.push_str("};\n");
    }
    d.push_str(
        "typedef struct { const char* module; const char* name; const char* sig; } FrImport;\n\
         typedef struct { u32 offset; u32 len; const u8* bytes; } FrData;\n\
         typedef struct { u32 version; u32 n_imports; const FrImport* imports; void** slots; u32 n_globals; const u64* ginit;\n\
         u64 mem_pages; u64 mem_max; u32 n_data; const FrData* data; void (*start)(Inst*); u32 n_tags; } FrModule;\n",
    );
    d.push_str("static const FrImport IMPORTS[] = {\n");
    for (md, nm, t) in &m.imports {
        let sig = m.types[*t as usize].as_ref().unwrap();
        writeln!(d, "  {{ {}, {}, \"{}\" }},", c_str(md), c_str(nm), sig_string(sig)).unwrap();
    }
    d.push_str("  { 0, 0, 0 } };\nstatic const FrData DATA[] = {\n");
    for (k, (off, bytes)) in m.data.iter().enumerate() {
        writeln!(d, "  {{ {off}u, {}u, D{k} }},", bytes.len()).unwrap();
    }
    d.push_str("  { 0, 0, 0 } };\nstatic const u64 GINIT[] = {");
    for (_, _, v) in &m.globals {
        write!(d, " 0x{v:016x}ull,").unwrap();
    }
    d.push_str(" 0 };\n");
    let start = m.start.unwrap() as usize;
    writeln!(
        d,
        "__attribute__((visibility(\"default\"))) const FrModule fr_module = {{ 1, {}, IMPORTS, IMPS, {}, GINIT, {}ull, {}ull, {}, DATA, wf{start}, {} }};",
        m.nimp,
        m.globals.len(),
        m.mem.0,
        m.mem.1.unwrap_or(u64::MAX),
        m.data.len(),
        m.tags.len()
    )
    .unwrap();

    // function units, split by body size
    let total: usize = m.bodies.iter().map(|b| (b.range().end - b.range().start) as usize).sum();
    let per = total / units.max(1) + 1;
    let mut out = vec![d];
    let mut cur = String::from("#include \"mod.h\"\n");
    let mut size = 0;
    for (k, b) in m.bodies.iter().enumerate() {
        let f = m.nimp + k;
        cur.push_str(&gen_function(&m, bulk, f, b)?);
        size += (b.range().end - b.range().start) as usize;
        if size >= per {
            out.push(std::mem::replace(&mut cur, String::from("#include \"mod.h\"\n")));
            size = 0;
        }
    }
    if size > 0 {
        out.push(cur);
    }
    Ok(CModule { header: h, units: out })
}

/// Offsets of the module's bulk memory operators (to check the Cranelift record covers them).
pub fn bulk_offsets(wasm: &[u8]) -> Result<Vec<u32>> {
    let mut v = vec![];
    for p in Parser::new(0).parse_all(wasm) {
        if let Payload::CodeSectionEntry(b) = p? {
            let mut r = b.get_operators_reader()?;
            while !r.eof() {
                let (op, off) = r.read_with_offset()?;
                if matches!(op, Operator::MemoryCopy { .. } | Operator::MemoryFill { .. }) {
                    v.push(off as u32);
                }
            }
        }
    }
    Ok(v)
}
