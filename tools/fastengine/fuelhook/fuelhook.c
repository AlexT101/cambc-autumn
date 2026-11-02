// LD_PRELOAD hook on cambc 4.0.0's wasm_runtime::charge_fuel(caller, amount): counts every host-call charge by
// (return address, amount), so each import's call count and fuel price can be read off a real game without
// changing it (the hook adds time, not fuel). Output: FUELHOOK_OUT (default fuelhook.tsv), one line per key:
//   <return address offset in cambc, hex> <amount> <count>
// With FUELHOOK_TRAMPOLINES=tramp.tsv (make_tramp_table.py) it also counts every host call, by patching the entry of
// each import's wasmtime array_call_trampoline; counts go to FUELHOOK_CALLS (default fuelhook-calls.tsv):
//   <trampoline offset in cambc, hex> <calls>
// Build: cc -O2 -shared -fPIC -o fuelhook.so fuelhook.c
// Only an executable named cambc is touched, and the patch site's 12 displaced bytes are checked first, so any
// other cambc build is left alone (offsets are cambc 4.0.0's).
#define _GNU_SOURCE
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define CHARGE_FUEL 0x43a1d00UL
static const unsigned char k_prologue[12] = {0x41, 0x57, 0x41, 0x56, 0x53, 0x48, 0x83, 0xec, 0x10, 0x48, 0x8b, 0x1f};

static uintptr_t g_base;
__attribute__((visibility("hidden"))) uintptr_t g_resume; // read by the stub

#define CAP (1 << 16)
static struct { uintptr_t ret; uint64_t amount; uint64_t count; } g_tab[CAP];
static uint64_t g_total;

__attribute__((visibility("hidden"))) void fuelhook_record(uint64_t amount, uintptr_t ret) {
    g_total++;
    uint64_t h = (ret * 0x9E3779B97F4A7C15ULL) ^ (amount * 0xC2B2AE3D27D4EB4FULL);
    for (uint64_t i = h & (CAP - 1);; i = (i + 1) & (CAP - 1)) {
        if (g_tab[i].count == 0) { g_tab[i].ret = ret; g_tab[i].amount = amount; g_tab[i].count = 1; return; }
        if (g_tab[i].ret == ret && g_tab[i].amount == amount) { g_tab[i].count++; return; }
    }
}

void fuelhook_stub(void);
__asm__(
    ".text\n.globl fuelhook_stub\nfuelhook_stub:\n"
    "  push %rdi\n  push %rsi\n  push %rdx\n  push %rcx\n  push %r8\n  push %r9\n  push %r10\n  push %r11\n  push %rax\n"
    "  mov 56(%rsp), %rdi\n"   // amount (the caller's rsi)
    "  mov 72(%rsp), %rsi\n"   // charge_fuel's return address
    "  call fuelhook_record\n"
    "  pop %rax\n  pop %r11\n  pop %r10\n  pop %r9\n  pop %r8\n  pop %rcx\n  pop %rdx\n  pop %rsi\n  pop %rdi\n"
    "  push %r15\n  push %r14\n  push %rbx\n  sub $0x10, %rsp\n  mov (%rdi), %rbx\n"  // the displaced prologue
    "  mov g_resume(%rip), %rax\n"  // rax is overwritten by the next original instruction
    "  jmp *%rax\n");

static int find_base(struct dl_phdr_info* info, size_t size, void* data) {
    (void)size; (void)data;
    if (info->dlpi_name && info->dlpi_name[0] == 0) { g_base = info->dlpi_addr; return 1; }
    return 0;
}

#define MAXT 1024
static uintptr_t g_toff[MAXT];
static uint64_t g_tcount[MAXT];
static int g_nt;

static void patch_trampolines(const char* table) {
    FILE* f = fopen(table, "r");
    if (!f) { perror("fuelhook: trampoline table"); return; }
    unsigned char* region = mmap(NULL, 1 << 20, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (region == MAP_FAILED) { perror("fuelhook mmap"); fclose(f); return; }
    unsigned char* w = region;
    unsigned long off; int ncopy;
    long pg = sysconf(_SC_PAGESIZE);
    while (g_nt < MAXT && fscanf(f, "%lx %d", &off, &ncopy) == 2) {
        unsigned char* site = (unsigned char*)(g_base + off);
        int i = g_nt++;
        g_toff[i] = off;
        unsigned char* thunk = w;
        uint64_t ctr = (uint64_t)(uintptr_t)&g_tcount[i];
        *w++ = 0x50;                                   // push rax
        *w++ = 0x48; *w++ = 0xB8; memcpy(w, &ctr, 8); w += 8;  // movabs rax, &count
        *w++ = 0x48; *w++ = 0xFF; *w++ = 0x00;         // inc qword [rax]
        *w++ = 0x58;                                   // pop rax
        memcpy(w, site, ncopy); w += ncopy;            // displaced instructions
        *w++ = 0xFF; *w++ = 0x25; memset(w, 0, 4); w += 4;  // jmp [rip+0]
        uint64_t resume = (uint64_t)(uintptr_t)(site + ncopy); memcpy(w, &resume, 8); w += 8;
        uintptr_t start = (uintptr_t)site & ~(uintptr_t)(pg - 1);
        mprotect((void*)start, 2 * pg, PROT_READ | PROT_WRITE | PROT_EXEC);
        unsigned char patch[32];
        memset(patch, 0xCC, sizeof patch);
        patch[0] = 0xFF; patch[1] = 0x25; memset(patch + 2, 0, 4);
        uint64_t t = (uint64_t)(uintptr_t)thunk; memcpy(patch + 6, &t, 8);
        memcpy(site, patch, ncopy);
        mprotect((void*)start, 2 * pg, PROT_READ | PROT_EXEC);
    }
    fclose(f);
}

static void dump(void) {
    const char* path = getenv("FUELHOOK_OUT");
    FILE* f = fopen(path ? path : "fuelhook.tsv", "w");
    if (!f) return;
    fprintf(f, "# total %llu\n", (unsigned long long)g_total);
    for (int i = 0; i < CAP; i++)
        if (g_tab[i].count)
            fprintf(f, "%lx %llu %llu\n", (unsigned long)(g_tab[i].ret - g_base), (unsigned long long)g_tab[i].amount,
                    (unsigned long long)g_tab[i].count);
    fclose(f);
    if (g_nt) {
        const char* cpath = getenv("FUELHOOK_CALLS");
        FILE* c = fopen(cpath ? cpath : "fuelhook-calls.tsv", "w");
        if (c) {
            for (int i = 0; i < g_nt; i++)
                if (g_tcount[i]) fprintf(c, "%lx %llu\n", (unsigned long)g_toff[i], (unsigned long long)g_tcount[i]);
            fclose(c);
        }
    }
}

__attribute__((constructor)) static void install(void) {
    char exe[512] = {0};
    // Only the cambc executable itself: LD_PRELOAD also reaches e.g. ~/.cache/cambc/wasi-sdk-33/bin/clang.
    if (readlink("/proc/self/exe", exe, sizeof exe - 1) <= 0) return;
    const char* slash = strrchr(exe, '/');
    if (strcmp(slash ? slash + 1 : exe, "cambc") != 0) return;
    dl_iterate_phdr(find_base, NULL);
    unsigned char* site = (unsigned char*)(g_base + CHARGE_FUEL);
    if (memcmp(site, k_prologue, sizeof k_prologue) != 0) { fprintf(stderr, "fuelhook: unexpected prologue, not patched\n"); return; }
    g_resume = (uintptr_t)site + 12;
    long pg = sysconf(_SC_PAGESIZE);
    uintptr_t start = (uintptr_t)site & ~(uintptr_t)(pg - 1);
    if (mprotect((void*)start, 2 * pg, PROT_READ | PROT_WRITE | PROT_EXEC)) { perror("fuelhook mprotect"); return; }
    unsigned char patch[12] = {0x48, 0xB8};
    uint64_t target = (uint64_t)(uintptr_t)fuelhook_stub;
    memcpy(patch + 2, &target, 8);
    patch[10] = 0xFF; patch[11] = 0xE0;  // jmp *%rax
    memcpy(site, patch, sizeof patch);
    mprotect((void*)start, 2 * pg, PROT_READ | PROT_EXEC);
    const char* table = getenv("FUELHOOK_TRAMPOLINES");
    if (table) patch_trampolines(table);
    atexit(dump);
}
