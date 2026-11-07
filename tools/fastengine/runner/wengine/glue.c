// The wasm engine backend's C side: one wasm2c instance of cambc's engine (tools/replay/engine/v3_0_0.wasm), its
// WASI imports (stubs: the engine needs no I/O), and the 7 wasm-rt functions the generated code calls, implemented
// here instead of linking libwasm-rt-impl, whose wasm_rt_init installs SIGSEGV/SIGBUS handlers over native mode's.
// The instance's whole state is its linear memory plus global g0 (the shadow-stack pointer): fr_w2c_snapshot /
// fr_w2c_restore copy exactly that.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "engine.h"

struct w2c_wasi__snapshot__preview1 { int unused; };
static struct w2c_wasi__snapshot__preview1 wasi;
static w2c_engine E;
static int E_ready;

#define W struct w2c_wasi__snapshot__preview1*
#define WASI_EBADF 8
u32 w2c_wasi__snapshot__preview1_environ_get(W w, u32 a, u32 b) { return 0; }
u32 w2c_wasi__snapshot__preview1_environ_sizes_get(W w, u32 count, u32 size) {
  memset(E.w2c_memory.data + count, 0, 4);
  memset(E.w2c_memory.data + size, 0, 4);
  return 0;
}
u32 w2c_wasi__snapshot__preview1_fd_close(W w, u32 a) { return WASI_EBADF; }
u32 w2c_wasi__snapshot__preview1_fd_fdstat_get(W w, u32 a, u32 b) { return WASI_EBADF; }
u32 w2c_wasi__snapshot__preview1_fd_prestat_dir_name(W w, u32 a, u32 b, u32 c) { return WASI_EBADF; }
u32 w2c_wasi__snapshot__preview1_fd_prestat_get(W w, u32 a, u32 b) { return WASI_EBADF; }
u32 w2c_wasi__snapshot__preview1_fd_read(W w, u32 a, u32 b, u32 c, u32 d) { return WASI_EBADF; }
u32 w2c_wasi__snapshot__preview1_fd_seek(W w, u32 a, u64 b, u32 c, u32 d) { return WASI_EBADF; }
u32 w2c_wasi__snapshot__preview1_fd_write(W w, u32 a, u32 b, u32 c, u32 d) { return WASI_EBADF; }
void w2c_wasi__snapshot__preview1_proc_exit(W w, u32 code) {
  fprintf(stderr, "fastrunner: wasm engine called proc_exit(%u)\n", code);
  abort();
}
u32 w2c_wasi__snapshot__preview1_random_get(W w, u32 buf, u32 len) {
  memset(E.w2c_memory.data + buf, 0, len);
  return 0;
}

// ---- wasm-rt: guard-page memory (engine.c is compiled without bounds checks), plain tables ----
#define PAGE 65536ull
#define RESERVE (8ull << 30)  // 4 GiB of address space plus 4 GiB of guard: any u32 address + u32 offset faults

bool wasm_rt_is_initialized(void) { return true; }

void wasm_rt_trap(wasm_rt_trap_t t) {
  fprintf(stderr, "fastrunner: wasm engine trapped (wasm_rt_trap %d)\n", (int)t);
  abort();
}

void wasm_rt_allocate_memory(wasm_rt_memory_t* m, uint64_t initial, uint64_t max, bool is64) {
  void* p = mmap(NULL, RESERVE, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
  if (p == MAP_FAILED || is64) {
    fprintf(stderr, "fastrunner: wasm engine memory reservation failed\n");
    abort();
  }
  if (initial && mprotect(p, initial * PAGE, PROT_READ | PROT_WRITE) != 0) abort();
  m->data = p;
  m->pages = initial;
  m->max_pages = max;
  m->size = initial * PAGE;
  m->is64 = false;
}

uint64_t wasm_rt_grow_memory(wasm_rt_memory_t* m, uint64_t delta) {
  uint64_t old = m->pages, n = old + delta;
  if (n < old || n > m->max_pages || n > 65536) return (uint64_t)-1;
  if (delta && mprotect(m->data + old * PAGE, delta * PAGE, PROT_READ | PROT_WRITE) != 0) return (uint64_t)-1;
  m->pages = n;
  m->size = n * PAGE;
  return old;
}

void wasm_rt_free_memory(wasm_rt_memory_t* m) { munmap(m->data, RESERVE); }

void wasm_rt_allocate_funcref_table(wasm_rt_funcref_table_t* t, uint32_t elements, uint32_t max) {
  t->data = calloc(elements ? elements : 1, sizeof(wasm_rt_funcref_t));
  t->size = elements;
  t->max_size = max;
}

void wasm_rt_free_funcref_table(wasm_rt_funcref_table_t* t) { free(t->data); }

// ---- the runner's interface ----
w2c_engine* fr_w2c_instance(void) {
  if (!E_ready) {
    wasm2c_engine_instantiate(&E, &wasi);
    w2c_engine_0x5Finitialize(&E);
    E_ready = 1;
  }
  return &E;
}
u8* fr_w2c_mem_base(void) { return E.w2c_memory.data; }
u64 fr_w2c_mem_size(void) { return E.w2c_memory.size; }
u32 fr_w2c_g0(void) { return E.w2c_g0; }

// A snapshot: the memory's first `size` bytes and g0. `buf` holds fr_w2c_mem_size() bytes.
void fr_w2c_snapshot(u8* buf, u32* g0) {
  memcpy(buf, E.w2c_memory.data, E.w2c_memory.size);
  *g0 = E.w2c_g0;
}

// Back to a snapshot of `size` bytes. Memory grown since is zeroed and the size set back, so a later memory.grow
// hands out zeroed pages again, as on the first run (those pages stay accessible; nothing else changes).
void fr_w2c_restore(const u8* buf, u64 size, u32 g0) {
  if (size > E.w2c_memory.size) {
    uint64_t d = (size - E.w2c_memory.size) / PAGE;
    if (wasm_rt_grow_memory(&E.w2c_memory, d) == (uint64_t)-1) abort();
  }
  if (E.w2c_memory.size > size) memset(E.w2c_memory.data + size, 0, E.w2c_memory.size - size);
  memcpy(E.w2c_memory.data, buf, size);
  E.w2c_memory.pages = size / PAGE;
  E.w2c_memory.size = size;
  E.w2c_g0 = g0;
}
