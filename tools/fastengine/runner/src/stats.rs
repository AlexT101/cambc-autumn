//! Match statistics (.camstat): runner::Game::statistics_bytes, done by calling cambc's own
//! runner::summary::{collect, encode} (we run inside the cambc executable), so the bytes are cambc's.
use crate::engine::{Eng, Game};
use anyhow::{anyhow, bail, Result};

type Collect = unsafe extern "C" fn(*mut [u64; 8], Game, *const u8, usize, u64, u64);
type Encode = unsafe extern "C" fn(*mut [u64; 4], *const [u64; 8]);
type DropValue = unsafe extern "C" fn(*mut [u64; 8]);

/// FNV-1a 64 of the map file (runner::Game's map hash; also its default-draft seed).
pub fn fnv1a(b: &[u8]) -> u64 {
    let mut h = 0xcbf29ce484222325u64;
    for &x in b {
        h = (h ^ x as u64).wrapping_mul(0x100000001b3);
    }
    h
}

/// `diagnostics`: the runner diagnostics (guest exits and traps) per team.
pub fn export(eng: &Eng, g: Game, map: &[u8], diagnostics: [u32; 2]) -> Result<Vec<u8>> {
    let sym = |n: &str| eng.syms.iter().find(|(k, _)| k.starts_with(n)).map(|(_, a)| eng.base + a);
    let collect = sym("_RNvNtCskEkT8JJjj5s_6runner7summary7collect").ok_or_else(|| anyhow!("no summary::collect"))?;
    let encode = sym("_RNvNtCskEkT8JJjj5s_6runner7summary6encode").ok_or_else(|| anyhow!("no summary::encode"))?;
    // serde_json::Value's drop glue as instantiated in the runner crate, at the address
    // runner::Game::statistics_bytes calls.
    let drop = eng.base + 0x41a7fe0; // cambc 5.0.1 (5.0.0: 0x4165900, 4.0.0: 0x415f940)
    let collect: Collect = unsafe { std::mem::transmute(collect) };
    let encode: Encode = unsafe { std::mem::transmute(encode) };
    let drop: DropValue = unsafe { std::mem::transmute(drop) };
    let sha = sha256_hex(map);
    let mut value = [0u64; 8];
    let packed = diagnostics[0] as u64 | (diagnostics[1] as u64) << 32;
    unsafe { collect(&mut value, g, sha.as_ptr(), sha.len(), fnv1a(map), packed) };
    if value[0] as u8 == 0xff {
        bail!("summary::collect failed");
    }
    let mut out = [0u64; 4];
    unsafe { encode(&mut out, &value) };
    unsafe { drop(&mut value) };
    if out[0] > isize::MAX as u64 {
        bail!("summary::encode failed");
    }
    let (cap, ptr, len) = (out[0], out[1] as *mut u8, out[2] as usize);
    let bytes = unsafe { std::slice::from_raw_parts(ptr, len) }.to_vec();
    if cap != 0 {
        unsafe { libc::free(ptr as *mut libc::c_void) };
    }
    Ok(bytes)
}

/// Lowercase hex SHA-256 (runner::Game keeps the map's digest for the summary).
fn sha256_hex(data: &[u8]) -> String {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98,
        0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
        0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8,
        0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
        0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
        0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut h: [u32; 8] =
        [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    let mut msg = data.to_vec();
    let bits = (data.len() as u64).wrapping_mul(8);
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bits.to_be_bytes());
    for chunk in msg.chunks(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes(chunk[4 * i..4 * i + 4].try_into().unwrap());
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16].wrapping_add(s0).wrapping_add(w[i - 7]).wrapping_add(s1);
        }
        let mut v = h;
        for i in 0..64 {
            let s1 = v[4].rotate_right(6) ^ v[4].rotate_right(11) ^ v[4].rotate_right(25);
            let ch = (v[4] & v[5]) ^ (!v[4] & v[6]);
            let t1 = v[7].wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0 = v[0].rotate_right(2) ^ v[0].rotate_right(13) ^ v[0].rotate_right(22);
            let maj = (v[0] & v[1]) ^ (v[0] & v[2]) ^ (v[1] & v[2]);
            let t2 = s0.wrapping_add(maj);
            v = [t1.wrapping_add(t2), v[0], v[1], v[2], v[3].wrapping_add(t1), v[4], v[5], v[6]];
        }
        for i in 0..8 {
            h[i] = h[i].wrapping_add(v[i]);
        }
    }
    h.iter().map(|x| format!("{x:08x}")).collect()
}
