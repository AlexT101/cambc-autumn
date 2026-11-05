//! cambc 5.0.0's native C++ game engine, loaded from the cambc binary itself.
//!
//! cambc is a PIE executable, which glibc refuses to dlopen; a copy with DF_1_PIE cleared loads. The
//! engine's C API (Game_*, Bitboard_*, DistanceField_*) is not in .dynsym, so addresses come from the
//! symbol table plus the load base.
use anyhow::{anyhow, bail, Result};
use object::{Object, ObjectSymbol};
use std::collections::HashMap;
use std::ffi::{c_char, c_void};

pub const CAMBC_BUILD_ID: &str = "f89c384317d66a7dec5afa7be5ebe98969e9f406";

pub type Game = u64;
/// Perspective: team in the low 32 bits, champion id in the high 32 (0xFFFFFFFF for a draft bot,
/// team 2 for the observer).
pub type Persp = u64;

pub fn persp(team: u32, champion: u32) -> Persp {
    team as u64 | (champion as u64) << 32
}

macro_rules! engine_fns {
    ($($name:ident : fn($($arg:ty),*) $(-> $ret:ty)?;)*) => {
        #[allow(non_snake_case)]
        pub struct Eng {
            $(pub $name: unsafe extern "C" fn($($arg),*) $(-> $ret)?,)*
            pub base: usize,
            pub syms: HashMap<String, usize>,
        }
        impl Eng {
            fn resolve(base: usize, syms: HashMap<String, usize>) -> Result<Eng> {
                Ok(Eng {
                    $($name: unsafe {
                        let a = *syms.get(stringify!($name)).ok_or_else(|| anyhow!("engine symbol {} missing", stringify!($name)))?;
                        std::mem::transmute::<usize, unsafe extern "C" fn($($arg),*) $(-> $ret)?>(base + a)
                    },)*
                    base,
                    syms,
                })
            }
        }
    };
}

engine_fns! {
    Game_FromMapFileBytes: fn(*const u8, usize, *mut Game) -> i32;
    Game_Destroy: fn(Game) -> i32;
    Game_Statistics_Enable: fn(Game) -> i32;
    Game_Statistics_RunnerEvent: fn(Game, u32, u32, u32) -> i32;
    Game_Runner_Init: fn(Game) -> i32;
    Game_Runner_GetState: fn(Game, *mut [u32; 4]) -> i32;
    Game_Runner_EndTurn: fn(Game, u32) -> i32;
    Game_Runner_Advance: fn(Game) -> i32;
    Game_Action_Resign: fn(Game) -> i32;
    Game_Action_Draft: fn(Game, u32) -> i32;
    Game_Visualiser_Timeline_GetMain: fn(Game, *mut u64) -> i32;
    Game_Visualiser_Timeline_Info: fn(Game, u64, *mut u32, *mut u64, *mut u32) -> i32;
    Game_API_Champion_GetNumAllies: fn(Game, Persp, *mut u32) -> i32;
    Game_API_Champion_GetAllies: fn(Game, Persp, *mut u32, u32, *mut u32) -> i32;
    Game_API_Champion_Get: fn(Game, Persp, u32, *mut u8) -> i32;
    Game_API_Map_GetBitboardMetadata: fn(Game, *mut [u32; 5]) -> i32;
    Bitboard_GetRawBufferSize: fn(*const [u32; 5], *mut u64) -> i32;
    DistanceField_GetRawBufferSize: fn(*const [u32; 5], *mut u64) -> i32;
    Game_SaveReplay: fn(Game) -> i32;
    Game_FileBuffer: fn(Game, *mut *const u8, *mut usize) -> i32;
    GetLastErrorMsg: fn() -> *const c_char;
    Game_Statistics_GetSummary: fn(Game, *mut u8) -> i32;
}

impl Eng {
    /// Address of any symbol by its mangled name (C API names are unmangled).
    pub fn sym(&self, name: &str) -> Option<usize> {
        self.syms.get(name).map(|a| self.base + a)
    }

    /// Typed lookup for engine functions the import layer resolves lazily.
    pub unsafe fn func<F: Copy>(&self, name: &str) -> Result<F> {
        assert_eq!(std::mem::size_of::<F>(), std::mem::size_of::<usize>());
        let a = self.sym(name).ok_or_else(|| anyhow!("engine symbol {name} missing"))?;
        Ok(std::mem::transmute_copy::<usize, F>(&a))
    }

    pub fn last_error(&self) -> String {
        unsafe {
            let p = (self.GetLastErrorMsg)();
            if p.is_null() {
                return String::new();
            }
            std::ffi::CStr::from_ptr(p).to_string_lossy().into_owned()
        }
    }
}

/// The engine's thread-local last error: Engine::Result stores its message pointer at fs:0 - 0x5f0 in cambc 5.0.0 (as in 4.0.0),
/// where GetLastErrorMsg reads it.
#[inline(always)]
pub fn err_slot() -> *mut *const u8 {
    let tp: usize;
    unsafe { std::arch::asm!("mov {}, fs:0", out(reg) tp, options(nostack, readonly, preserves_flags)) };
    (tp - 0x5f0) as *mut *const u8
}

fn build_id(elf: &object::File) -> Option<String> {
    elf.build_id().ok().flatten().map(|b| b.iter().map(|x| format!("{x:02x}")).collect())
}

/// Load bias of the main program (cambc).
fn exe_base() -> usize {
    unsafe extern "C" fn cb(info: *mut libc::dl_phdr_info, _size: usize, data: *mut c_void) -> i32 {
        *(data as *mut usize) = (*info).dlpi_addr as usize;
        1 // the main program comes first
    }
    let mut base = 0usize;
    unsafe { libc::dl_iterate_phdr(Some(cb), &mut base as *mut usize as *mut c_void) };
    base
}

/// The running executable, mapped read-only.
fn map_exe() -> Result<&'static [u8]> {
    let f = std::fs::File::open("/proc/self/exe")?;
    let len = f.metadata()?.len() as usize;
    use std::os::fd::AsRawFd;
    let p = unsafe { libc::mmap(std::ptr::null_mut(), len, libc::PROT_READ, libc::MAP_PRIVATE, f.as_raw_fd(), 0) };
    if p == libc::MAP_FAILED {
        bail!("mmap /proc/self/exe failed");
    }
    Ok(unsafe { std::slice::from_raw_parts(p as *const u8, len) })
}

/// Is this process cambc 5.0.0 (the build this runner was made for)?
pub fn is_cambc_process() -> bool {
    let Ok(b) = map_exe() else { return false };
    let ok = object::File::parse(b).ok().and_then(|e| build_id(&e)).map_or(false, |id| {
        id == CAMBC_BUILD_ID || std::env::var_os("FASTRUNNER_ANY_CAMBC").is_some()
    });
    unsafe { libc::munmap(b.as_ptr() as *mut c_void, b.len()) };
    ok
}

/// The engine inside the running cambc executable (we are preloaded into it).
pub fn load() -> Result<&'static Eng> {
    let bytes = map_exe()?;
    let elf = object::File::parse(bytes)?;
    let id = build_id(&elf).unwrap_or_default();
    if id != CAMBC_BUILD_ID && std::env::var_os("FASTRUNNER_ANY_CAMBC").is_none() {
        bail!("this process has build-id {id}, the runner was built against cambc 5.0.0 ({CAMBC_BUILD_ID})");
    }
    let mut syms = HashMap::new();
    for s in elf.symbols() {
        if let Ok(n) = s.name() {
            let wanted = n.starts_with("Game_")
                || n.starts_with("Bitboard_")
                || n.starts_with("DistanceField_")
                || n == "GetLastErrorMsg"
                || n.starts_with("_ZN6Engine6Result")
                || crate::patch::SYMS.contains(&n)
                || n.starts_with("_RNvNtCskEkT8JJjj5s_6runner7summary")
                || n.starts_with("_RINvNtCs2cIQpoOfIE0_4core3ptr9drop_glueNtNtCsjrEt3oldMzQ_10serde_json5value5ValueECskEkT8JJjj5s_6runner");
            if s.address() != 0 && wanted {
                syms.entry(n.to_string()).or_insert(s.address() as usize);
            }
        }
    }
    drop(elf);
    unsafe { libc::munmap(bytes.as_ptr() as *mut c_void, bytes.len()) };
    Ok(Box::leak(Box::new(Eng::resolve(exe_base(), syms)?)))
}
