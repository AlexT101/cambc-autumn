//! The replay bundle cambc writes: a zip of replay.repl26a, team-{a,b}.stdout, team-{a,b}.debug and
//! team-{a,b}.fuel, deflated, dated 1980-01-01. The members equal cambc's; the compressed bytes differ.
use std::io::Write;

pub fn fuel_file(turns: &[u64]) -> Vec<u8> {
    let mut v = Vec::with_capacity(13 + 64 + 8 * turns.len());
    v.extend_from_slice(b"a62leuf\0");
    v.extend_from_slice(&[0, 0, 1, 0, 0]); // version 1; both teams' language: cpp
    let q = crate::fuel::quantum() * crate::fuel::QUANTA_PER_TURN;
    for _ in 0..2 {
        for b in [100 * q, q, 2 * q, q] {
            v.extend_from_slice(&b.to_le_bytes());
        }
    }
    for t in turns {
        v.extend_from_slice(&t.to_le_bytes());
    }
    v
}

/// Raw deflate at libdeflate's level 1: ~1.5x miniz_oxide's level 1 in speed, and members ~25% smaller.
fn deflate(data: &[u8]) -> Vec<u8> {
    thread_local! {
        static C: std::cell::RefCell<libdeflater::Compressor> =
            std::cell::RefCell::new(libdeflater::Compressor::new(libdeflater::CompressionLvl::new(1).unwrap()));
    }
    C.with(|c| {
        let mut c = c.borrow_mut();
        let mut out = vec![0u8; c.deflate_compress_bound(data.len())];
        let n = c.deflate_compress(data, &mut out).expect("the bound fits");
        out.truncate(n);
        out
    })
}

pub fn zip(members: &[(&str, &[u8])]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut central = Vec::new();
    for (name, data) in members {
        let crc = crc32fast::hash(data);
        let comp = deflate(data);
        let off = out.len() as u32;
        let local = |w: &mut Vec<u8>, sig: u32, central: bool| {
            w.extend_from_slice(&sig.to_le_bytes());
            if central {
                w.extend_from_slice(&(0x0314u16).to_le_bytes()); // made by: unix, 2.0
            }
            w.extend_from_slice(&20u16.to_le_bytes()); // version needed 2.0
            w.extend_from_slice(&0u16.to_le_bytes()); // flags
            w.extend_from_slice(&8u16.to_le_bytes()); // deflate
            w.extend_from_slice(&0u16.to_le_bytes()); // time 00:00
            w.extend_from_slice(&0x21u16.to_le_bytes()); // date 1980-01-01
            w.extend_from_slice(&crc.to_le_bytes());
            w.extend_from_slice(&(comp.len() as u32).to_le_bytes());
            w.extend_from_slice(&(data.len() as u32).to_le_bytes());
            w.extend_from_slice(&(name.len() as u16).to_le_bytes());
            w.extend_from_slice(&0u16.to_le_bytes()); // extra
            if central {
                w.extend_from_slice(&0u16.to_le_bytes()); // comment
                w.extend_from_slice(&0u16.to_le_bytes()); // disk
                w.extend_from_slice(&0u16.to_le_bytes()); // internal attrs
                w.extend_from_slice(&((0o100644u32) << 16).to_le_bytes()); // external attrs
                w.extend_from_slice(&off.to_le_bytes());
            }
            w.extend_from_slice(name.as_bytes());
        };
        local(&mut out, 0x04034b50, false);
        out.extend_from_slice(&comp);
        local(&mut central, 0x02014b50, true);
    }
    let cd_off = out.len() as u32;
    out.extend_from_slice(&central);
    out.extend_from_slice(&0x06054b50u32.to_le_bytes());
    out.extend_from_slice(&[0, 0, 0, 0]);
    out.extend_from_slice(&(members.len() as u16).to_le_bytes());
    out.extend_from_slice(&(members.len() as u16).to_le_bytes());
    out.extend_from_slice(&(central.len() as u32).to_le_bytes());
    out.extend_from_slice(&cd_off.to_le_bytes());
    out.extend_from_slice(&0u16.to_le_bytes());
    out
}

pub fn write_bundle(path: &std::path::Path, r: &crate::game::MatchResult) -> std::io::Result<()> {
    let fa = fuel_file(&r.fuel[0]);
    let fb = fuel_file(&r.fuel[1]);
    let z = zip(&[
        ("replay.repl26a", &r.replay),
        ("team-a.stdout", &r.stdout[0]),
        ("team-b.stdout", &r.stdout[1]),
        ("team-a.debug", b""),
        ("team-b.debug", b""),
        ("team-a.fuel", &fa),
        ("team-b.fuel", &fb),
    ]);
    if let Some(d) = path.parent() {
        if !d.as_os_str().is_empty() {
            std::fs::create_dir_all(d)?;
        }
    }
    let tmp = path.with_extension("repl26a.part");
    let mut f = std::fs::File::create(&tmp)?;
    f.write_all(&z)?;
    drop(f);
    std::fs::rename(tmp, path)
}
