// Feasibility probe: load cambc 4.0.0's native C++ game engine as a library and call it directly.
// cambc is a PIE executable, which glibc refuses to dlopen; a copy with DF_1_PIE cleared loads.
// The engine's C API (Game_*) is not in .dynsym, so addresses come from the symbol table (nm) + the load base.
//   cc -O2 -o dlengine dlengine.c -ldl
//   ./dlengine CAMBC_COPY_WITHOUT_PIE_FLAG NM_SYMS MAP.map26a
#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static uintptr_t sym(const char* syms, const char* name) {
    FILE* f = fopen(syms, "r");
    char line[4096];
    size_t n = strlen(name);
    while (fgets(line, sizeof line, f)) {
        // "<addr> [<size>] <kind> <name>"
        char* last = strrchr(line, ' ');
        if (!last) continue;
        if (strncmp(last + 1, name, n) == 0 && (last[1 + n] == '\n' || last[1 + n] == 0)) {
            fclose(f);
            return strtoull(line, NULL, 16);
        }
    }
    fclose(f);
    return 0;
}

int main(int argc, char** argv) {
    void* h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 1; }
    struct link_map* lm;
    dlinfo(h, RTLD_DI_LINKMAP, &lm);
    uintptr_t base = lm->l_addr;
    printf("loaded at %#lx\n", (unsigned long)base);
    int (*from_map)(const uint8_t*, size_t, uint64_t*, int) = (void*)(base + sym(argv[2], "Game_FromMapFileBytes"));
    int (*num_groups)(uint64_t, uint32_t*) = (void*)(base + sym(argv[2], "Game_API_Map_GetNumCampGroups"));
    int (*round)(uint64_t, uint32_t*) = (void*)(base + sym(argv[2], "Game_API_GetRoundNumber"));
    int (*destroy)(uint64_t) = (void*)(base + sym(argv[2], "Game_Destroy"));
    FILE* f = fopen(argv[3], "rb");
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t* buf = malloc(len); fread(buf, 1, len, f); fclose(f);
    setvbuf(stdout, NULL, _IONBF, 0);
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    uint64_t g = 0;
    int rc = from_map(buf, len, &g, 0);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    int (*runner_init)(uint64_t) = (void*)(base + sym(argv[2], "Game_Runner_Init"));
    printf("Game_Runner_Init rc=%d\n", runner_init(g));
    uint32_t ng = 0, nc = 0;
    int rc2 = num_groups(g, &ng), rc3 = round(g, &nc);
    printf("Game_FromMapFileBytes rc=%d handle=%#llx (%.1f us); camp groups rc=%d n=%u; round rc=%d n=%u\n", rc,
           (unsigned long long)g, (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3, rc2, ng, rc3, nc);
    printf("destroy rc=%d\n", destroy(g));
    return 0;
}
