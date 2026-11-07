//! Touched-page scans for memory the runner resets or restores many times (bot linear memories): PAGEMAP_SCAN
//! (Linux 6.7+) lists the pages of a range that may hold non-zero bytes, so a reset zeroes and a snapshot saves only
//! those. Without the kernel support (or with FASTRUNNER_TOUCHED=0) callers treat every page as touched.
//!
//! Tried and dropped: userfaultfd async write-protection, to rewrite only the pages written since a snapshot. A
//! bot writes ~100 of the ~350 pages a fork snapshot holds, and the engine ~25 of its ~500, but re-protecting a
//! bot's memory costs ~40 us, registering its reservation ~10 ms and each first write a fault (~0.45 us), so CPU
//! time came out the same or worse than copying the pages.
use std::sync::OnceLock;

const PAGEMAP_SCAN: u64 = 0xc0606610;
const PAGE_IS_PRESENT: u64 = 8;
const PAGE_IS_SWAPPED: u64 = 16;
const PAGE_IS_PFNZERO: u64 = 32;

pub const PAGE: usize = 4096;

#[repr(C)]
struct PmScanArg {
    size: u64,
    flags: u64,
    start: u64,
    end: u64,
    walk_end: u64,
    vec: u64,
    vec_len: u64,
    max_pages: u64,
    category_inverted: u64,
    category_mask: u64,
    category_anyof_mask: u64,
    return_mask: u64,
}
#[repr(C)]
#[derive(Clone, Copy, Default)]
struct PageRegion {
    start: u64,
    end: u64,
    categories: u64,
}

/// /proc/self/pagemap, for PAGEMAP_SCAN (None: unavailable, or FASTRUNNER_TOUCHED=0).
fn pagemap() -> Option<i32> {
    static P: OnceLock<Option<i32>> = OnceLock::new();
    *P.get_or_init(|| {
        if std::env::var("FASTRUNNER_TOUCHED").is_ok_and(|v| v == "0") {
            return None;
        }
        let fd = unsafe { libc::open(c"/proc/self/pagemap".as_ptr(), libc::O_RDONLY | libc::O_CLOEXEC) };
        if fd < 0 {
            return None;
        }
        // The kernel must know PAGEMAP_SCAN (Linux 6.7+): probe an empty range.
        let mut a = scan_arg(0, 0, 0, 0, 0, std::ptr::null_mut(), 0);
        (unsafe { libc::ioctl(fd, PAGEMAP_SCAN as _, &mut a) } >= 0).then_some(fd)
    })
}

fn scan_arg(start: u64, end: u64, inverted: u64, mask: u64, anyof: u64, vec: *mut PageRegion, n: usize) -> PmScanArg {
    PmScanArg {
        size: std::mem::size_of::<PmScanArg>() as u64,
        flags: 0,
        start,
        end,
        walk_end: 0,
        vec: vec as u64,
        vec_len: n as u64,
        max_pages: 0,
        category_inverted: inverted,
        category_mask: mask,
        category_anyof_mask: anyof,
        return_mask: anyof | mask,
    }
}

/// Calls `f(first page, end page)` for each run of pages of [base, base + len) that may hold non-zero bytes:
/// present (other than the shared zero page) or swapped out. Every other page of an anonymous private mapping
/// reads as zero (never touched, or dropped by MADV_DONTNEED), so a memory known to have been all zero at some
/// point differs from zero only in these pages since. False if the scan is unavailable or failed (the caller then
/// treats every page as touched).
pub fn touched(base: *mut u8, len: usize, mut f: impl FnMut(usize, usize)) -> bool {
    let Some(pm) = pagemap() else { return false };
    let mut regs = [PageRegion::default(); 256];
    let end = base as u64 + len as u64;
    let mut start = base as u64;
    while start < end {
        let mut a = scan_arg(start, end, PAGE_IS_PFNZERO, PAGE_IS_PFNZERO, PAGE_IS_PRESENT | PAGE_IS_SWAPPED, regs.as_mut_ptr(), regs.len());
        let n = unsafe { libc::ioctl(pm, PAGEMAP_SCAN as _, &mut a) };
        if n < 0 {
            return false;
        }
        for r in &regs[..n as usize] {
            f(((r.start - base as u64) as usize) / PAGE, ((r.end - base as u64) as usize) / PAGE);
        }
        if (n as usize) < regs.len() || a.walk_end >= end || a.walk_end <= start {
            break;
        }
        start = a.walk_end;
    }
    true
}

/// A set of page indices, kept as a list and a bitmap (membership in O(1), iteration over the list).
#[derive(Clone, Default)]
pub struct PageSet {
    bits: Vec<u64>,
    pub list: Vec<u32>,
}

impl PageSet {
    pub fn insert(&mut self, p: usize) -> bool {
        let w = p / 64;
        if w >= self.bits.len() {
            self.bits.resize(w + 1, 0);
        }
        let m = 1u64 << (p % 64);
        if self.bits[w] & m != 0 {
            return false;
        }
        self.bits[w] |= m;
        self.list.push(p as u32);
        true
    }
    pub fn len(&self) -> usize {
        self.list.len()
    }
}
