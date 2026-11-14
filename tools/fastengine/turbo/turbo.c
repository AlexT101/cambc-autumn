// Speed up stock cambc 4.0.0 in-process (LD_PRELOAD) without changing any game, replay or fuel.
// research/notes/FASTENGINE-DESIGN.md (§5, §9) has the measurements and the parity runs.
//
// Patch 1, altar_locks: cambc's import calls runner::engine::ffi::visible_altar_locks(game, persp_a, persp_b,
// out, cap, count_out). It reads the bitboard metadata, then for the ally and then the enemy altar-lock occupancy
// board tests every tile (y outer, x inner) and calls Game_API_GetAltarLock for each set bit, then stable-sorts
// the 24-byte records by the u32 at offset 4 and copies them out. The fast path makes the same engine calls in the
// same order, visiting only set bits (skipping empty chunks) in the same tile order, and returns what the original
// returns; on any engine error it reruns the original, whose calls then come last, so the engine's state (its last
// error included) ends as the original leaves it.
//
// Patch 2, export lookup: imports fetch the bot's memory with Caller::get_export("memory") (and champion_out with
// "champion_query_memory", absent for C++ bots), which runs wasmtime's Instance::get_export: two SipHash lookups.
// An instance's exports never change, so a Memory (a plain store id + index) or an absent export is cached per
// (store, store id, instance index, name). Other results (SharedMemory holds reference counts) are not cached.
//
// Patch 3, guest memory: runner::api::memory and the seven runner::api::primitives::guest_ptr::<T> (a bounds and
// alignment check on a guest pointer) each resolve the memory through the export lookup, the store's instance
// table and Memory::internal_data_size. The fast versions resolve the instance's VMMemoryDefinition pointer once
// (it is fixed for the instance's life), then read base and length from it on every call and apply the same checks.
//
// Patch 4, read memo: Game_API_Champion_Get (a quarter of all host calls, with heavy stat breakdowns) is answered
// from a cache keyed by (game, perspective, id, out present) while the game is unchanged. The engine is reached
// only through its GOT slots (no direct calls or other references exist in this build), so every engine entry
// point that is not a verified pure read is wrapped to advance an epoch that invalidates the cache. A hit returns
// the cached code, copies the cached 44-byte record on success (the engine writes nothing on failure), and sets
// the engine's thread-local last-error pointer as the call left it. TURBO_CHECK=1 also makes the real call on every
// hit and aborts on any difference.
//
// Build: cc -O2 -shared -fPIC -o turbo.so turbo.c
// Use:   LD_PRELOAD=/abs/turbo.so cambc run ...     (or CAMBC_TURBO, tools/cambc_env.py)
// Env:   TURBO_OFF=1 disables all; TURBO_NO_ALTAR, TURBO_NO_EXPORT, TURBO_NO_GUEST, TURBO_NO_MEMO one each;
//        TURBO_VERBOSE=1 reports counts at exit; TURBO_CHECK=1 cross-checks memo hits.
// It patches only an executable with cambc 4.0.0's GNU build-id (LD_PRELOAD also reaches python, cmake and the
// wasi-sdk clang under ~/.cache/cambc, which it must leave alone), and checks every function it replaces or relies
// on byte for byte (FNV-1a of the whole function) and every GOT slot it rewrites.
#define _GNU_SOURCE
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

// cambc 4.0.0 offsets, valid only for this build-id.
// BuildID 207dc99706e05b507e6cdbd9b635c8aa937ce18a
static const unsigned char k_build_id[20] = {0x20, 0x7d, 0xc9, 0x97, 0x06, 0xe0, 0x5b, 0x50, 0x7e, 0x6c,
                                             0xdb, 0xd9, 0xb6, 0x35, 0xc8, 0xaa, 0x93, 0x7c, 0xe1, 0x8a};

enum { F_ALTAR, F_GET_EXPORT, F_GP_BUFF, F_GP_ITEM, F_GP_SETTINGS, F_GP_U64, F_GP_U8, F_GP_I32, F_GP_U16, F_MEMORY,
       F_CO_TELEPORT, F_CO_I32, F_CO_U32, F_RESULT, F_CHAMPION_GET, F_DATA_SIZE, F_COUNT };
// Offset, size, FNV-1a 64 of the bytes, and how many prologue bytes a jump displaces (0: not patched, only relied on).
static const struct { uintptr_t off; uint32_t size; uint64_t fnv; uint32_t ncopy; } k_funcs[F_COUNT] = {
    {0x404a5e0UL, 0x640, 0xf6ff120a8417064aULL, 17},  // runner::engine::ffi::visible_altar_locks
    {0x403d610UL, 0xfa, 0x3fb2e0227c7b4eddULL, 14},   // Instance::get_export::<&mut StoreContextMut<GuestCtx>>
    {0x40430b0UL, 0x23a, 0x48f9426d756b4359ULL, 14},  // guest_ptr::<BuffData>            (12-byte elements)
    {0x40432f0UL, 0x23a, 0x9c93c4a71589fc22ULL, 14},  // guest_ptr::<GameItemInfo>        (40)
    {0x4043530UL, 0x23a, 0xda621664ae3885eeULL, 14},  // guest_ptr::<GameSettings>        (120)
    {0x4043770UL, 0x238, 0xa5a39c91e9276310ULL, 14},  // guest_ptr::<u64> = <GameConsumableInfo> (8)
    {0x40439b0UL, 0x227, 0x511bdced5a133227ULL, 14},  // guest_ptr::<u8>                  (1)
    {0x4043be0UL, 0x238, 0xd6b148ae914b647dULL, 14},  // guest_ptr::<i32> = <u32>         (4)
    {0x4043e20UL, 0x22f, 0xb4110c3c6e89e181ULL, 14},  // guest_ptr::<u16>                 (2)
    {0x4169270UL, 0x190, 0x30e2d593abe8cc71ULL, 14},  // runner::api::memory
    {0x415fac0UL, 0x1eb, 0xd7b956ad51018077ULL, 14},  // champion_out::<GameTeleport>     (28)
    {0x415fcb0UL, 0x1eb, 0x563614ef5024bd3aULL, 14},  // champion_out::<i32>              (4)
    {0x415fea0UL, 0x1eb, 0xe781bbb5d0de8de2ULL, 14},  // champion_out::<u32>              (4)
    {0x41b43b0UL, 0x27, 0xca6d9d25ceb1ae0fULL, 0},    // Engine::Result: last error in TLS at %fs:0 - 0x5f0
    {0x4194a00UL, 0x176, 0x969d40140c376b6aULL, 0},   // Game_API_Champion_Get: writes 44 bytes only on success
    {0x45651e0UL, 0x91, 0xf8e69ea92cb1c5c4ULL, 0},    // Memory::internal_data_size: the chain resolve_def follows
};
#define OFF_MAP_METADATA 0x419b200UL
#define OFF_ALLY_LOCK_OCC 0x419e220UL
#define OFF_ENEMY_LOCK_OCC 0x419e650UL
#define OFF_GET_ALTAR_LOCK 0x419a570UL
#define OFF_GOT_CHAMPION_GET 0x5280518UL
#define TLS_LAST_ERROR 0x5f0

// Every GOT slot that holds an engine entry point (all 183 R_X86_64_RELATIVE relocations whose target is an engine
// export; there are none outside .got and no direct or lea references from the runner), with the target, and 1 if
// the function cannot change game state: Bitboard_* and DistanceField_* take no game, and the listed Game_API
// reads only reach const Engine::Game methods or plain accessors (Runtime, Health).
static const struct { uint32_t slot, target; uint8_t pure; } k_got[] = {
    {0x5280160, 0x419b200, 1},  // Game_API_Map_GetBitboardMetadata
    {0x5280168, 0x41b4410, 1},  // Bitboard_GetRawBufferSize
    {0x5280170, 0x41b4e60, 1},  // DistanceField_GetRawBufferSize
    {0x5280190, 0x41b43e0, 1},  // GetLastErrorMsg
    {0x52801a8, 0x419bd10, 0},  // Game_API_GetWards
    {0x52801b0, 0x419e220, 1},  // Game_API_GetAllyAltarLockOccupancy
    {0x52801b8, 0x419a570, 1},  // Game_API_GetAltarLock
    {0x52801c0, 0x419e650, 1},  // Game_API_GetEnemyAltarLockOccupancy
    {0x52801d0, 0x419ea80, 0},  // Game_API_GetTeleports
    {0x52801d8, 0x4183730, 0},  // Game_FromMapFileBytes
    {0x52801e0, 0x4194100, 1},  // Game_API_Camp_GetBuffs
    {0x52801e8, 0x419c460, 0},  // Game_API_GetControlWards
    {0x52801f0, 0x4191720, 0},  // Game_API_ReadDraftMemory
    {0x52801f8, 0x41914e0, 1},  // Game_API_ReadSharedMemory
    {0x5280200, 0x4191840, 0},  // Game_API_WriteDraftMemory
    {0x5280208, 0x4194fd0, 0},  // Game_API_Champion_GetBuffs
    {0x5280210, 0x4196a00, 1},  // Game_API_Champion_GetItems
    {0x5280218, 0x4192500, 0},  // Game_API_Map_GetCampGroups
    {0x5280220, 0x4191600, 0},  // Game_API_WriteSharedMemory
    {0x5280228, 0x4197a00, 0},  // Game_API_Champion_GetAllies
    {0x5280230, 0x4197d00, 0},  // Game_API_Champion_GetEnemies
    {0x5280238, 0x4196bb0, 1},  // Game_API_Champion_GetConsumables
    {0x5280240, 0x419d050, 0},  // Game_API_Map_CampGroup_GetCampInfo
    {0x5280248, 0x418a400, 0},  // Game_SaveReplay
    {0x5280250, 0x418a4f0, 0},  // Game_FileBuffer
    {0x52802c0, 0x41892e0, 0},  // Game_Action_Recall
    {0x52802c8, 0x4189410, 0},  // Game_Action_CancelChannel
    {0x52802d0, 0x41890c0, 0},  // Game_Action_Resign
    {0x52802e8, 0x4191b80, 0},  // Game_API_Map_GetBushBitboard
    {0x52802f0, 0x4191d70, 0},  // Game_API_Map_GetWallBitboard
    {0x52802f8, 0x4191f60, 0},  // Game_API_Map_GetAltarBitboard
    {0x5280300, 0x4192150, 0},  // Game_API_Map_GetHoleBitboard
    {0x5280308, 0x4189cb0, 0},  // Game_Action_Sell
    {0x5280310, 0x41934b0, 1},  // Game_API_GetVision
    {0x5280318, 0x4197080, 1},  // Game_API_GetCampOccupancy
    {0x5280320, 0x4197190, 0},  // Game_API_GetAwakeCampOccupancy
    {0x5280328, 0x4197290, 0},  // Game_API_GetAsleepCampOccupancy
    {0x5280330, 0x4197390, 1},  // Game_API_GetAllyOccupancy
    {0x5280338, 0x41974a0, 1},  // Game_API_GetEnemyOccupancy
    {0x5280340, 0x41975b0, 0},  // Game_API_GetAllyWardOccupancy
    {0x5280348, 0x41976c0, 0},  // Game_API_GetAllyControlWardOccupancy
    {0x5280350, 0x41977d0, 0},  // Game_API_GetEnemyWardOccupancy
    {0x5280358, 0x41978e0, 0},  // Game_API_GetEnemyControlWardOccupancy
    {0x5280360, 0x419dfe0, 1},  // Game_API_GetTeleportOccupancy
    {0x5280368, 0x4191960, 0},  // Game_API_GetSharedMemorySize
    {0x5280370, 0x4191a70, 0},  // Game_API_GetDraftMemorySize
    {0x5280378, 0x4189f10, 0},  // Game_Action_BuyConsumable
    {0x5280380, 0x41891b0, 0},  // Game_Action_SetPriority
    {0x5280388, 0x41984b0, 1},  // Game_API_GetSubmittedGemCount
    {0x5280390, 0x41994c0, 0},  // Game_API_Draft_GetCurrentRound
    {0x5280398, 0x4199640, 0},  // Game_API_Draft_GetNumRounds
    {0x52803a0, 0x419b4a0, 0},  // Game_API_Draft_GetCurrentTeam
    {0x52803a8, 0x4188fb0, 0},  // Game_Action_Draft
    {0x52803b0, 0x4192340, 0},  // Game_API_Map_GetNumCampGroups
    {0x52803b8, 0x4198680, 0},  // Game_API_Champion_GetNumAllies
    {0x52803c0, 0x4198cc0, 0},  // Game_API_Champion_GetNumEnemies
    {0x52803c8, 0x4191320, 0},  // Game_API_GetSettings
    {0x52803d0, 0x41b6680, 1},  // Bitboard_Zero
    {0x52803d8, 0x41b4d20, 1},  // Bitboard_Print
    {0x52803e0, 0x41b67c0, 1},  // Bitboard_One
    {0x52803e8, 0x41b5770, 1},  // DistanceField_Print
    {0x52803f0, 0x419b360, 1},  // Game_API_GetRoundNumber
    {0x52803f8, 0x419b0d0, 0},  // Game_API_Map_GetSymmetry
    {0x5280408, 0x41b6a70, 1},  // Bitboard_NumSetBits
    {0x5280410, 0x418a9b0, 0},  // Game_API_Champion_GetMovementMask
    {0x5280418, 0x41897b0, 0},  // Game_Action_Move
    {0x5280420, 0x4189650, 0},  // Game_Action_Attack
    {0x5280428, 0x4189b80, 0},  // Game_Action_SubmitGems
    {0x5280430, 0x419a730, 0},  // Game_API_Champion_GetTeleport
    {0x5280438, 0x419c660, 0},  // Game_API_Champion_Design
    {0x5280440, 0x419ca20, 0},  // Game_API_Camp_Design
    {0x5280448, 0x4194e70, 0},  // Game_API_Champion_GetRestrictions
    {0x5280450, 0x419a1e0, 1},  // Game_API_Champion_GetWards
    {0x5280458, 0x4189de0, 0},  // Game_Action_BuyItem
    {0x5280460, 0x418a230, 0},  // Game_Action_PlaceWard
    {0x5280468, 0x4198000, 1},  // Game_API_Champion_IsAlive
    {0x5280470, 0x4194b80, 0},  // Game_API_Champion_GetIdentity
    {0x5280478, 0x4196240, 0},  // Game_API_Ward_Get
    {0x5280480, 0x41964b0, 0},  // Game_API_ControlWard_Get
    {0x5280488, 0x41966e0, 1},  // Game_API_Champion_GetGold
    {0x5280490, 0x4196890, 1},  // Game_API_Champion_GetGems
    {0x5280498, 0x4198160, 0},  // Game_API_Champion_GetRespawnTimer
    {0x52804a0, 0x41957b0, 0},  // Game_API_Champion_CanSell
    {0x52804a8, 0x419a9b0, 1},  // Game_API_Champion_GetChannelTime
    {0x52804b0, 0x419ad20, 0},  // Game_API_Map_CampGroup_GetRespawnTime
    {0x52804b8, 0x41982e0, 0},  // Game_API_GetSpawnRegion
    {0x52804c0, 0x4193bd0, 1},  // Game_API_Camp_GetState
    {0x52804c8, 0x419d360, 1},  // Game_API_CampGroup_GetState
    {0x52804d0, 0x419d780, 0},  // Game_API_CampGroup_GetCaptureState
    {0x52804d8, 0x419d560, 0},  // Game_API_CampGroup_GetCooldown
    {0x52804e0, 0x419cd70, 0},  // Game_API_Map_CampGroup_GetNumCamps
    {0x52804e8, 0x4193f80, 0},  // Game_API_Camp_GetNumBuffs
    {0x52804f0, 0x4194cf0, 0},  // Game_API_Champion_GetNumBuffs
    {0x52804f8, 0x4192760, 0},  // Game_API_Map_CampGroup_Get
    {0x5280500, 0x4192980, 0},  // Game_API_Map_CampInfo_Get
    {0x5280508, 0x4192ba0, 0},  // Game_API_Map_CampInfo_GetGroup
    {0x5280510, 0x4193d80, 1},  // Game_API_Camp_Get
    {0x5280518, 0x4194a00, 1},  // Game_API_Champion_Get
    {0x5280520, 0x4191490, 0},  // Game_API_GetConsumableInfo
    {0x5280528, 0x41913e0, 0},  // Game_API_GetItemInfo
    {0x5280530, 0x41b6900, 1},  // Bitboard_IsZero
    {0x5280538, 0x41b6e10, 1},  // Bitboard_Not
    {0x5280540, 0x41b58b0, 1},  // DistanceField_Copy
    {0x5280548, 0x419db20, 0},  // Game_API_GetVisionMask
    {0x5280550, 0x4199760, 0},  // Game_API_Champion_GetAbilityDamage
    {0x5280558, 0x41999c0, 0},  // Game_API_Champion_GetAbilityHeal
    {0x5280560, 0x4199c20, 0},  // Game_API_Champion_GetAbilityShield
    {0x5280568, 0x4199e80, 0},  // Game_API_Champion_GetAbilityProps
    {0x5280570, 0x419a030, 0},  // Game_API_Camp_GetAbilityProps
    {0x5280578, 0x4192ff0, 0},  // Game_API_GetWardVisionMask
    {0x5280580, 0x4193250, 0},  // Game_API_GetControlWardVisionMask
    {0x5280588, 0x419a380, 0},  // Game_API_IsOccupiedByTeleport
    {0x5280590, 0x419ee20, 0},  // Game_API_GetTeleport
    {0x5280598, 0x41955f0, 0},  // Game_API_Champion_CanShop
    {0x52805a0, 0x418a050, 0},  // Game_Action_UseConsumable
    {0x52805a8, 0x4193740, 0},  // Game_API_InVision
    {0x52805b0, 0x41938f0, 1},  // Game_API_HasCamp
    {0x52805b8, 0x4194720, 0},  // Game_API_HasChampion
    {0x52805c0, 0x4195960, 0},  // Game_API_HasWard
    {0x52805c8, 0x4195ad0, 0},  // Game_API_HasControlWard
    {0x52805d0, 0x4196ef0, 0},  // Game_API_Champion_GetCharges
    {0x52805d8, 0x4195c40, 0},  // Game_API_GetAllyWard
    {0x52805e0, 0x4195dc0, 0},  // Game_API_GetEnemyWard
    {0x52805e8, 0x4195f40, 0},  // Game_API_GetAllyControlWard
    {0x52805f0, 0x41960c0, 0},  // Game_API_GetEnemyControlWard
    {0x52805f8, 0x4196d60, 1},  // Game_API_Champion_GetCooldown
    {0x5280600, 0x4199320, 0},  // Game_API_Draft_Get
    {0x5280610, 0x4192dc0, 0},  // Game_API_Map_GetCampAt
    {0x5280618, 0x4193a60, 0},  // Game_API_GetCamp
    {0x5280620, 0x4194890, 0},  // Game_API_GetChampion
    {0x5280628, 0x41b4520, 1},  // Bitboard_ImportRawBuffer
    {0x5280630, 0x41b4920, 1},  // Bitboard_ImportLinearBuffer
    {0x5280638, 0x41b4720, 1},  // Bitboard_ExportRawBuffer
    {0x5280640, 0x41b4b20, 1},  // Bitboard_ExportLinearBuffer
    {0x5280648, 0x41b6150, 1},  // Bitboard_Toggle
    {0x5280650, 0x41b7610, 1},  // Bitboard_Union
    {0x5280658, 0x41b7980, 1},  // Bitboard_Intersect
    {0x5280660, 0x41b7cf0, 1},  // Bitboard_Xor
    {0x5280668, 0x41b8040, 1},  // Bitboard_IsEqual
    {0x5280670, 0x41b6ff0, 1},  // Bitboard_ShiftRight
    {0x5280678, 0x41b71e0, 1},  // Bitboard_ShiftUp
    {0x5280680, 0x41b73d0, 1},  // Bitboard_Reflect
    {0x5280688, 0x41b4f70, 1},  // DistanceField_ImportRawBuffer
    {0x5280690, 0x41b5370, 1},  // DistanceField_ImportLinearBuffer
    {0x5280698, 0x41b5170, 1},  // DistanceField_ExportRawBuffer
    {0x52806a0, 0x41b5570, 1},  // DistanceField_ExportLinearBuffer
    {0x52806a8, 0x41b5aa0, 1},  // DistanceField_CopyWithMask
    {0x52806b0, 0x419aba0, 1},  // Game_API_Champion_GetPriority
    {0x52806b8, 0x41b5dc0, 1},  // Bitboard_Test
    {0x52806c0, 0x41b6be0, 1},  // Bitboard_GetSetBits
    {0x52806c8, 0x4199880, 0},  // Game_API_Champion_GetAbilityDamageAgainst
    {0x52806d0, 0x4199ae0, 0},  // Game_API_Champion_GetAbilityHealAgainst
    {0x52806d8, 0x4199d40, 0},  // Game_API_Champion_GetAbilityShieldAgainst
    {0x52806e0, 0x419f0c0, 0},  // Game_API_Champion_GetWardPositions
    {0x52806e8, 0x41b5f90, 1},  // Bitboard_Set
    {0x52806f8, 0x41b8280, 1},  // Bitboard_DrawCircle
    {0x5280700, 0x41b8450, 1},  // Bitboard_DrawManhattan
    {0x5280708, 0x41b8620, 1},  // Bitboard_DrawChebyshev
    {0x5280710, 0x41b6300, 1},  // DistanceField_Get
    {0x5280718, 0x41b64d0, 1},  // DistanceField_Set
    {0x5280720, 0x41b87f0, 1},  // Bitboard_ReflectHorizontalPosition
    {0x5280728, 0x41b8960, 1},  // Bitboard_ReflectVerticalPosition
    {0x5280730, 0x41b8ad0, 1},  // Bitboard_Rotate180Position
    {0x5280738, 0x419dd00, 1},  // Game_API_Champion_GetBuffData
    {0x5280740, 0x4189980, 0},  // Game_Action_Cast
    {0x5280748, 0x41b8c40, 1},  // Bitboard_ReachableMaskWithExpansionCount
    {0x5280750, 0x41b96a0, 1},  // Bitboard_ShadowCastWithScanCount
    {0x5280758, 0x41b9a40, 1},  // DistanceField_ComputeWithExpansionCount
    {0x5280760, 0x41b8f90, 1},  // Bitboard_ReachableMaskWithScratchAndExpansionCount
    {0x5280768, 0x41ba170, 1},  // DistanceField_ComputeToWithExpansionCount
    {0x5280778, 0x4183cb0, 0},  // Game_Destroy
    {0x5280780, 0x418eb50, 0},  // Game_Statistics_GetSummary
    {0x5280788, 0x418ee00, 0},  // Game_Statistics_GetChampion
    {0x5280790, 0x4181e40, 0},  // Game_Runner_Init
    {0x5280798, 0x4189540, 0},  // Game_Runner_Advance
    {0x52807a0, 0x4188ed0, 0},  // Game_Runner_EndTurn
    {0x52807a8, 0x4181f30, 0},  // Game_Runner_GetState
    {0x52807b0, 0x418f550, 0},  // Game_Visualiser_Timeline_GetMain
    {0x52807b8, 0x418f650, 0},  // Game_Visualiser_Timeline_Info
    {0x52807c8, 0x418f300, 0},  // Game_Statistics_Records
    {0x52807d0, 0x418f1b0, 0},  // Game_Statistics_EndPosition
    {0x5280890, 0x418ef00, 0},  // Game_Statistics_Enable
    {0x52808b0, 0x418f020, 0},  // Game_Statistics_RunnerEvent
};

static uintptr_t g_base;
static int g_build_id_ok;
// The main program's executable segment, page-aligned. Patches are written with the whole segment made writable at
// once, so the kernel reports one mapping change covering it all: profilers (samply) then keep cambc's symbols,
// where a partial mprotect splits the mapping and they drop it.
static uintptr_t g_text_lo, g_text_hi;
static int g_verbose, g_check;

// ---------------------------------------------------------------------------------------------------------------
// Patch 1: altar locks

typedef int (*metadata_fn)(uint64_t game, void* out);
typedef int (*occupancy_fn)(uint64_t game, uint64_t persp, void* board);
typedef int (*getlock_fn)(uint64_t game, uint64_t persp, uint32_t x, uint32_t y, uint32_t team, void* out24);
typedef int (*altar_fn)(uint64_t game, uint32_t a, uint32_t b, void* out, uint64_t cap, uint32_t* count);

static metadata_fn g_metadata;
static occupancy_fn g_ally_occ, g_enemy_occ;
static getlock_fn g_get_lock;
static altar_fn g_altar_orig;
static uint64_t g_altar_none, g_altar_some;

static int fast_altar_locks(uint64_t game, uint32_t a, uint32_t b, void* out, uint64_t cap, uint32_t* count) {
    // Bitboard metadata as the original reads it: width, height at +0, +4; chunk rows, columns at +0xc, +0x10.
    int32_t meta[16] = {0};
    if (g_metadata(game, meta) != 0) return g_altar_orig(game, a, b, out, cap, count);
    const int32_t w = meta[0], h = meta[1];
    const uint64_t cols = (uint32_t)meta[4], chunks = (uint64_t)(uint32_t)meta[3] * cols;
    const uint64_t bytes = (chunks - chunks / 2) * 16;
    static __attribute__((aligned(16))) uint64_t board[1 << 13];
    static unsigned char recs[24 * 4096];
    if (bytes > sizeof board) return g_altar_orig(game, a, b, out, cap, count);
    const uint64_t persp = ((uint64_t)b << 32) | a;
    const uint64_t ncx = w > 0 ? ((uint64_t)w + 7) / 8 : 0;
    uint64_t n = 0;
    for (int pass = 0; pass < 2; pass++) {
        occupancy_fn occ = pass == 0 ? g_ally_occ : g_enemy_occ;
        if (occ(game, persp, board) != 0) return g_altar_orig(game, a, b, out, cap, count);
        const uint32_t team = pass == 0 ? (a == 2 ? 0 : a) : (a == 2 ? 1 : 1 - a);
        if (h <= 0 || w <= 0) continue;
        // The original's order: y ascending, then x ascending. A chunk holds rows y..y+7 of 8 columns, a byte a row.
        for (int32_t y0 = 0; y0 < h; y0 += 8) {
            const uint64_t* crow = board + (uint64_t)(y0 >> 3) * cols;
            uint64_t any = 0;
            for (uint64_t cx = 0; cx < ncx; cx++) any |= crow[cx];
            if (!any) continue;
            for (int32_t y = y0; y < h && y < y0 + 8; y++) {
                for (uint64_t cx = 0; cx < ncx; cx++) {
                    uint64_t row = (crow[cx] >> ((y & 7) * 8)) & 0xff;
                    while (row) {
                        const uint32_t x = (uint32_t)(cx * 8 + __builtin_ctzll(row));
                        row &= row - 1;
                        if (x >= (uint32_t)w) break;
                        if (n >= sizeof recs / 24) return g_altar_orig(game, a, b, out, cap, count);
                        unsigned char* r = recs + 24 * n;
                        memset(r, 0, 24);
                        const int rc = g_get_lock(game, persp, x, (uint32_t)y, team, r);
                        if (a == 2 && rc == 98) continue;
                        if (rc != 0) return g_altar_orig(game, a, b, out, cap, count);
                        n++;
                    }
                }
            }
        }
    }
    // Stable sort by the u32 at offset 4, as sort_by_key.
    for (uint64_t i = 1; i < n; i++) {
        unsigned char t[24];
        memcpy(t, recs + 24 * i, 24);
        const uint32_t k = *(uint32_t*)(t + 4);
        uint64_t j = i;
        while (j > 0 && *(uint32_t*)(recs + 24 * (j - 1) + 4) > k) {
            memcpy(recs + 24 * j, recs + 24 * (j - 1), 24);
            j--;
        }
        memcpy(recs + 24 * j, t, 24);
    }
    if (n) g_altar_some++; else g_altar_none++;
    if (cap != 0) {
        if (cap < n) return 0x6f;
        memcpy(out, recs, 24 * n);
    }
    *count = (uint32_t)n;
    return 0;
}

// ---------------------------------------------------------------------------------------------------------------
// Patch 2: export lookup cache

// get_export(out: *mut Option<Extern> (32 bytes), instance: &Instance {store id u64, index u32},
//            store: &mut StoreContextMut (points at the store pointer), name ptr, name len)
typedef void* (*get_export_fn)(void* out, const void* instance, void** store_ctx, const char* name, size_t len);
static get_export_fn g_get_export;  // the original (trampoline), or the original itself if unpatched
static uint64_t g_export_hits, g_export_misses;
#define EXT_NONE(e) (*(const uint32_t*)(e) == 0xffffffffu)   // Option<Extern>::None niche
#define EXT_MEMORY(e) (*(const uint64_t*)(e) == 3)          // Extern::Memory
#define EXPORT_CACHE 64
static struct { void* store; uint64_t id; uint32_t index, name; int used; unsigned char value[32]; } g_exports[EXPORT_CACHE];

static void* fast_get_export(void* out, const void* instance, void** store_ctx, const char* name, size_t len) {
    uint32_t which;
    if (len == 6 && memcmp(name, "memory", 6) == 0) which = 1;
    else if (len == 21 && memcmp(name, "champion_query_memory", 21) == 0) which = 2;
    else return g_get_export(out, instance, store_ctx, name, len);
    void* store = *store_ctx;
    const uint64_t id = *(const uint64_t*)instance;
    const uint32_t index = *(const uint32_t*)((const char*)instance + 8);
    const unsigned slot = (unsigned)((id * 31 + index * 7 + which) & (EXPORT_CACHE - 1));
    for (unsigned k = 0; k < EXPORT_CACHE; k++) {
        unsigned i = (slot + k) & (EXPORT_CACHE - 1);
        if (!g_exports[i].used) break;
        if (g_exports[i].store == store && g_exports[i].id == id && g_exports[i].index == index &&
            g_exports[i].name == which) {
            g_export_hits++;
            memcpy(out, g_exports[i].value, 32);
            return out;
        }
    }
    g_export_misses++;
    g_get_export(out, instance, store_ctx, name, len);
    if (EXT_NONE(out) || EXT_MEMORY(out)) {
        for (unsigned k = 0; k < EXPORT_CACHE; k++) {
            unsigned i = (slot + k) & (EXPORT_CACHE - 1);
            if (!g_exports[i].used) {
                g_exports[i].used = 1; g_exports[i].store = store; g_exports[i].id = id; g_exports[i].index = index;
                g_exports[i].name = which;
                memcpy(g_exports[i].value, out, 32);
                break;
            }
        }
    }
    return out;
}

// ---------------------------------------------------------------------------------------------------------------
// Patch 3: guest memory

// A wasmtime Caller<GuestCtx>: the store pointer, then the caller's Instance {store id u64, index u32}.
// resolve_def finds the caller's "memory" VMMemoryDefinition {base, current_length}, or NULL where the original
// would not find a plain Memory (it then runs instead). The chain is runner::api::memory's and internal_data_size's.
// cqm_none records that the instance has no "champion_query_memory" export (champion_out then uses "memory").
static struct mdef { void* store; uint64_t id; uint32_t index, cqm_none; const uint64_t* def; } g_mdefs[64];
static struct mdef* g_mdef_last;
static uint64_t g_mdef_misses;

static const uint64_t* resolve_def(void** caller) {
    unsigned char ext[32];
    fast_get_export(ext, caller + 1, caller, "memory", 6);
    if (!EXT_MEMORY(ext)) return NULL;
    const uint64_t mem_store_id = *(const uint64_t*)(ext + 8);
    const uint32_t inst = *(const uint32_t*)(ext + 0x10), memidx = *(const uint32_t*)(ext + 0x18);
    const char* st = (const char*)caller[0];
    if (*(const uint64_t*)(st + 0x4c0) != mem_store_id) return NULL;             // original: panic
    if ((uint64_t)inst >= *(const uint64_t*)(st + 0x530)) return NULL;           // original: index panic
    const char* entry = *(const char* const*)(*(const char* const*)(st + 0x528) + (uint64_t)inst * 16);
    const char* offsets = *(const char* const*)(entry + 0x10);
    const uint64_t sel = *(const uint8_t*)(entry + 8) ? 0x28 : 0x70;
    if (memidx >= *(const uint32_t*)(offsets + sel + 0x18)) return NULL;         // original: panic
    const uint32_t off = memidx * 8u + *(const uint32_t*)(offsets + sel + 0x34);
    return *(const uint64_t* const*)(entry + 0x80 + (uint64_t)off);
}

static __attribute__((noinline)) struct mdef* mdef_slow(void** caller) {
    void* store = caller[0];
    const uint64_t id = (uint64_t)caller[1];
    const uint32_t index = *(const uint32_t*)(caller + 2);
    const unsigned slot = (unsigned)((id * 31 + index) & 63);
    struct mdef* m;
    for (unsigned k = 0; k < 64; k++) {
        m = &g_mdefs[(slot + k) & 63];
        if (!m->def) break;
        if (m->store == store && m->id == id && m->index == index) return g_mdef_last = m;
    }
    g_mdef_misses++;
    const uint64_t* def = resolve_def(caller);
    if (!def) return NULL;
    unsigned char ext[32];
    fast_get_export(ext, caller + 1, caller, "champion_query_memory", 21);
    for (unsigned k = 0; k < 64; k++) {
        m = &g_mdefs[(slot + k) & 63];
        if (!m->def) {
            m->store = store; m->id = id; m->index = index; m->def = def; m->cqm_none = EXT_NONE(ext);
            return g_mdef_last = m;
        }
    }
    return NULL;
}

static inline struct mdef* mdef_of(void** caller) {
    struct mdef* m = g_mdef_last;
    if (__builtin_expect(m && m->store == caller[0] && m->id == (uint64_t)caller[1] &&
                         m->index == *(const uint32_t*)(caller + 2), 1))
        return m;
    return mdef_slow(caller);
}

// runner::api::memory(out: *mut Option<&mut [u8]>, caller) -> out
typedef void* (*memory_fn)(uint64_t* out, void** caller);
static memory_fn g_memory_orig;
static void* fast_memory(uint64_t* out, void** caller) {
    const struct mdef* m = mdef_of(caller);
    if (!m) return g_memory_orig(out, caller);
    const uint64_t* def = m->def;
    out[0] = def[0];
    out[1] = def[1];
    return out;
}

// guest_ptr::<T>(out: *mut Result<*mut T, i32>, caller, ptr: i32, count: usize, align: usize) -> out
typedef void* (*guest_ptr_fn)(uint32_t* out, void** caller, uint32_t ptr, uint64_t count, uint64_t align);
static guest_ptr_fn g_gp_orig[7];
static inline void* guest_ptr(int which, uint64_t size, uint32_t* out, void** caller, uint32_t ptr, uint64_t count,
                              uint64_t align) {
    const struct mdef* m = mdef_of(caller);
    if (!m) return g_gp_orig[which](out, caller, ptr, count, align);
    const uint64_t base = m->def[0], len = m->def[1];
    uint64_t bytes, end;
    if ((int32_t)ptr < 0 || __builtin_mul_overflow(count, size, &bytes) ||
        __builtin_add_overflow(bytes, (uint64_t)ptr, &end) || (ptr == 0 && bytes != 0) || end > len || align == 0 ||
        (base + ptr) % align != 0) {
        out[1] = 0xffffffffu;
        out[0] = 1;
        return out;
    }
    *(uint64_t*)(out + 2) = base + ptr;
    out[0] = 0;
    return out;
}
#define GUEST_PTR(name, which, size) \
    static void* name(uint32_t* out, void** caller, uint32_t ptr, uint64_t count, uint64_t align) { \
        return guest_ptr(which, size, out, caller, ptr, count, align); \
    }
GUEST_PTR(gp_buff, 0, 12)
GUEST_PTR(gp_item, 1, 40)
GUEST_PTR(gp_settings, 2, 120)
GUEST_PTR(gp_u64, 3, 8)
GUEST_PTR(gp_u8, 4, 1)
GUEST_PTR(gp_i32, 5, 4)
GUEST_PTR(gp_u16, 6, 2)

// champion_out::<T>(out: *mut Result<*mut T, i32>, caller, ptr: i32) -> out: a pointer into the instance's
// "champion_query_memory" if it has one (then the original runs), else into "memory": ptr >= 0, ptr + size within
// the length, address 4-aligned (no null check, unlike guest_ptr).
typedef void* (*champion_out_fn)(uint32_t* out, void** caller, uint32_t ptr);
static champion_out_fn g_co_orig[3];
static inline void* champion_out(int which, uint64_t size, uint32_t* out, void** caller, uint32_t ptr) {
    const struct mdef* m = mdef_of(caller);
    if (!m || !m->cqm_none) return g_co_orig[which](out, caller, ptr);
    const uint64_t base = m->def[0], len = m->def[1];
    if ((int32_t)ptr < 0 || (uint64_t)ptr + size > len || ((base + ptr) & 3) != 0) {
        out[1] = 0xffffffffu;
        out[0] = 1;
        return out;
    }
    *(uint64_t*)(out + 2) = base + ptr;
    out[0] = 0;
    return out;
}
#define CHAMPION_OUT(name, which, size) \
    static void* name(uint32_t* out, void** caller, uint32_t ptr) { return champion_out(which, size, out, caller, ptr); }
CHAMPION_OUT(co_teleport, 0, 28)
CHAMPION_OUT(co_i32, 1, 4)
CHAMPION_OUT(co_u32, 2, 4)

// ---------------------------------------------------------------------------------------------------------------
// Patch 4: read memo

static uint64_t g_epoch = 1;  // advanced by every engine call that may change game state
static uint64_t g_memo_hits, g_memo_misses;

static inline const char** last_error_slot(void) {
    char* tp;
    __asm__("mov %%fs:0, %0" : "=r"(tp));
    return (const char**)(tp - TLS_LAST_ERROR);
}

typedef int (*champion_get_fn)(uint64_t game, uint64_t persp, uint32_t id, void* out44);
static champion_get_fn g_champion_get;
#define CHAMP_SIZE 44
static struct champ_memo {
    uint64_t epoch, game, persp;
    uint32_t id, has_out;
    int32_t rc;
    const char* msg;
    unsigned char out[CHAMP_SIZE];
} g_champ[512];

static void check_failed(const char* what, uint64_t game, uint64_t persp, uint32_t id) {
    fprintf(stderr, "turbo: TURBO_CHECK mismatch in %s (game %llx persp %llx id %u)\n", what, (unsigned long long)game,
            (unsigned long long)persp, id);
    abort();
}

static int memo_champion_get(uint64_t game, uint64_t persp, uint32_t id, void* out) {
    const uint32_t has_out = out != NULL;
    struct champ_memo* e = &g_champ[(id * 0x9E3779B1u ^ (uint32_t)persp * 0x85EBCA6Bu ^ (uint32_t)(persp >> 32) ^
                                     (uint32_t)game ^ has_out) & 511];
    if (e->epoch == g_epoch && e->game == game && e->persp == persp && e->id == id && e->has_out == has_out) {
        g_memo_hits++;
        if (g_check) {
            unsigned char probe[CHAMP_SIZE + 16];
            memset(probe, 0xA5, sizeof probe);
            if (has_out) memcpy(probe, out, CHAMP_SIZE);
            const int rc = g_champion_get(game, persp, id, has_out ? probe : NULL);
            if (rc != e->rc || *last_error_slot() != e->msg) check_failed("Champion_Get rc/last error", game, persp, id);
            if (has_out && memcmp(probe, e->rc == 0 ? e->out : (const unsigned char*)out, CHAMP_SIZE) != 0)
                check_failed("Champion_Get record", game, persp, id);
            for (int i = CHAMP_SIZE; i < CHAMP_SIZE + 16; i++)
                if (probe[i] != 0xA5) check_failed("Champion_Get wrote past 44 bytes", game, persp, id);
        }
        if (e->rc == 0 && has_out) memcpy(out, e->out, CHAMP_SIZE);
        *last_error_slot() = e->msg;
        return e->rc;
    }
    g_memo_misses++;
    const int rc = g_champion_get(game, persp, id, out);
    e->epoch = g_epoch; e->game = game; e->persp = persp; e->id = id; e->has_out = has_out;
    e->rc = rc;
    e->msg = *last_error_slot();
    if (rc == 0 && has_out) memcpy(e->out, out, CHAMP_SIZE);
    return rc;
}

// ---------------------------------------------------------------------------------------------------------------
// Installation

static uint64_t fnv1a(const unsigned char* p, size_t n) {
    uint64_t h = 0xcbf29ce484222325ULL;
    for (size_t i = 0; i < n; i++) h = (h ^ p[i]) * 0x100000001b3ULL;
    return h;
}

// The main program (empty name): its load base, executable segment, and whether its NT_GNU_BUILD_ID is cambc 4.0.0's.
static int find_base(struct dl_phdr_info* info, size_t size, void* data) {
    (void)size; (void)data;
    if (!info->dlpi_name || info->dlpi_name[0] != 0) return 0;
    g_base = info->dlpi_addr;
    const uintptr_t pg = (uintptr_t)sysconf(_SC_PAGESIZE);
    for (int i = 0; i < info->dlpi_phnum; i++) {
        const ElfW(Phdr)* ph = &info->dlpi_phdr[i];
        if (ph->p_type == PT_LOAD && (ph->p_flags & PF_X) && !g_text_lo) {
            g_text_lo = (info->dlpi_addr + ph->p_vaddr) & ~(pg - 1);
            g_text_hi = (info->dlpi_addr + ph->p_vaddr + ph->p_memsz + pg - 1) & ~(pg - 1);
        }
        if (ph->p_type != PT_NOTE) continue;
        const unsigned char* p = (const unsigned char*)(info->dlpi_addr + ph->p_vaddr);
        const unsigned char* end = p + ph->p_memsz;
        while (p + 12 <= end) {
            uint32_t namesz, descsz, type;
            memcpy(&namesz, p, 4); memcpy(&descsz, p + 4, 4); memcpy(&type, p + 8, 4);
            const unsigned char* name = p + 12;
            const unsigned char* desc = name + ((namesz + 3) & ~3u);
            if (type == 3 && namesz == 4 && memcmp(name, "GNU", 4) == 0 && descsz == sizeof k_build_id &&
                memcmp(desc, k_build_id, sizeof k_build_id) == 0)
                g_build_id_ok = 1;
            p = desc + ((descsz + 3) & ~3u);
        }
    }
    return 1;
}

// One RWX page holds the trampolines (displaced prologues) and the GOT thunks.
static unsigned char* g_code;
static size_t g_code_used, g_code_size;

static unsigned char* code_alloc(size_t n) {
    if (!g_code) {
        g_code_size = 4 * (size_t)sysconf(_SC_PAGESIZE);
        g_code = mmap(NULL, g_code_size, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (g_code == MAP_FAILED) { g_code = NULL; return NULL; }
    }
    if (g_code_used + n > g_code_size) return NULL;
    unsigned char* p = g_code + g_code_used;
    g_code_used = (g_code_used + n + 15) & ~(size_t)15;
    return p;
}

static int text_writable_begin(void) {
    return mprotect((void*)g_text_lo, g_text_hi - g_text_lo, PROT_READ | PROT_WRITE | PROT_EXEC);
}

static void text_writable_end(void) { mprotect((void*)g_text_lo, g_text_hi - g_text_lo, PROT_READ | PROT_EXEC); }

static int func_ok(int f) {
    const unsigned char* p = (const unsigned char*)(g_base + k_funcs[f].off);
    return fnv1a(p, k_funcs[f].size) == k_funcs[f].fnv;
}

// Redirect function f to target; returns a pointer that runs the original (displaced prologue, then a jump back),
// or NULL. The text must be writable and the function verified.
static void* patch_jump(int f, void* target) {
    unsigned char* site = (unsigned char*)(g_base + k_funcs[f].off);
    const size_t ncopy = k_funcs[f].ncopy;
    unsigned char* t = code_alloc(ncopy + 14);
    if (!t || ncopy < 14) return NULL;
    memcpy(t, site, ncopy);
    unsigned char* w = t + ncopy;
    *w++ = 0xFF; *w++ = 0x25; memset(w, 0, 4); w += 4;  // jmp [rip+0]
    uint64_t back = (uint64_t)(uintptr_t)(site + ncopy); memcpy(w, &back, 8);
    unsigned char p[32];
    memset(p, 0xCC, sizeof p);
    p[0] = 0xFF; p[1] = 0x25; memset(p + 2, 0, 4);
    uint64_t to = (uint64_t)(uintptr_t)target; memcpy(p + 6, &to, 8);
    memcpy(site, p, ncopy);
    return t;
}

// A thunk that advances the epoch, then jumps to the engine function: movabs &g_epoch, %r11; lock incq (%r11);
// movabs target, %r11; jmp *%r11. It touches only r11 (call-clobbered, never an argument) and flags.
static void* epoch_thunk(void* target) {
    unsigned char* t = code_alloc(27);
    if (!t) return NULL;
    unsigned char* w = t;
    uint64_t v = (uint64_t)(uintptr_t)&g_epoch;
    *w++ = 0x49; *w++ = 0xBB; memcpy(w, &v, 8); w += 8;
    *w++ = 0xF0; *w++ = 0x49; *w++ = 0xFF; *w++ = 0x03;
    v = (uint64_t)(uintptr_t)target;
    *w++ = 0x49; *w++ = 0xBB; memcpy(w, &v, 8); w += 8;
    *w++ = 0x41; *w++ = 0xFF; *w++ = 0xE3;
    return t;
}

static void install_memo(void) {
    const size_t n = sizeof k_got / sizeof k_got[0];
    uintptr_t lo = UINTPTR_MAX, hi = 0;
    for (size_t i = 0; i < n; i++) {
        void** slot = (void**)(g_base + k_got[i].slot);
        if ((uintptr_t)*slot != g_base + k_got[i].target) {
            fprintf(stderr, "turbo: unexpected GOT slot %x, read memo off\n", k_got[i].slot);
            return;
        }
        if ((uintptr_t)slot < lo) lo = (uintptr_t)slot;
        if ((uintptr_t)slot + 8 > hi) hi = (uintptr_t)slot + 8;
    }
    if (!func_ok(F_RESULT)) return;
    // The memoised reads: GOT slot, the function's k_funcs entry, its wrapper, where the original goes.
    const struct { uintptr_t slot; int f; void* wrapper; void** orig; } memo[] = {
        {OFF_GOT_CHAMPION_GET, F_CHAMPION_GET, (void*)memo_champion_get, (void**)&g_champion_get},
    };
    void* repl[sizeof k_got / sizeof k_got[0]];
    for (size_t i = 0; i < n; i++) {
        void* target = (void*)(g_base + k_got[i].target);
        size_t m = 0;
        while (m < sizeof memo / sizeof memo[0] && memo[m].slot != k_got[i].slot) m++;
        if (m < sizeof memo / sizeof memo[0] && k_got[i].pure && g_base + k_funcs[memo[m].f].off == (uintptr_t)target &&
            func_ok(memo[m].f)) {
            *memo[m].orig = target;
            repl[i] = memo[m].wrapper;
        } else if (k_got[i].pure) {
            repl[i] = target;
        } else if (!(repl[i] = epoch_thunk(target))) {
            return;
        }
    }
    const uintptr_t pg = (uintptr_t)sysconf(_SC_PAGESIZE);
    lo &= ~(pg - 1);
    hi = (hi + pg - 1) & ~(pg - 1);
    if (mprotect((void*)lo, hi - lo, PROT_READ | PROT_WRITE)) return;
    for (size_t i = 0; i < n; i++) *(void**)(g_base + k_got[i].slot) = repl[i];
    mprotect((void*)lo, hi - lo, PROT_READ);
}

static void report(void) {
    if (!g_verbose) return;
    fprintf(stderr,
            "turbo: altar_locks without/with locks %llu/%llu; export cache hits %llu misses %llu; memory def misses "
            "%llu; read memo hits %llu misses %llu; epoch %llu\n",
            (unsigned long long)g_altar_none, (unsigned long long)g_altar_some, (unsigned long long)g_export_hits,
            (unsigned long long)g_export_misses, (unsigned long long)g_mdef_misses, (unsigned long long)g_memo_hits,
            (unsigned long long)g_memo_misses, (unsigned long long)g_epoch);
}

__attribute__((constructor)) static void install(void) {
    if (getenv("TURBO_OFF")) return;
    dl_iterate_phdr(find_base, NULL);
    if (!g_build_id_ok || !g_text_lo) return;
    g_verbose = getenv("TURBO_VERBOSE") != NULL;
    g_check = getenv("TURBO_CHECK") != NULL;
    int ok[F_COUNT];
    for (int f = 0; f < F_COUNT; f++) ok[f] = func_ok(f);
    for (int f = 0; f < F_COUNT; f++)
        if (!ok[f]) fprintf(stderr, "turbo: cambc function at %lx differs from 4.0.0's; its patch is off\n",
                            (unsigned long)k_funcs[f].off);
    g_get_export = (get_export_fn)(g_base + k_funcs[F_GET_EXPORT].off);
    if (text_writable_begin()) return;
    if (ok[F_ALTAR] && !getenv("TURBO_NO_ALTAR")) {
        g_metadata = (metadata_fn)(g_base + OFF_MAP_METADATA);
        g_ally_occ = (occupancy_fn)(g_base + OFF_ALLY_LOCK_OCC);
        g_enemy_occ = (occupancy_fn)(g_base + OFF_ENEMY_LOCK_OCC);
        g_get_lock = (getlock_fn)(g_base + OFF_GET_ALTAR_LOCK);
        g_altar_orig = (altar_fn)patch_jump(F_ALTAR, (void*)fast_altar_locks);
    }
    if (ok[F_GET_EXPORT] && !getenv("TURBO_NO_EXPORT")) {
        void* orig = patch_jump(F_GET_EXPORT, (void*)fast_get_export);
        if (orig) g_get_export = (get_export_fn)orig;
    }
    if (ok[F_GET_EXPORT] && ok[F_DATA_SIZE] && !getenv("TURBO_NO_GUEST")) {
        static void* const fast[7] = {gp_buff, gp_item, gp_settings, gp_u64, gp_u8, gp_i32, gp_u16};
        for (int i = 0; i < 7; i++)
            if (ok[F_GP_BUFF + i]) g_gp_orig[i] = (guest_ptr_fn)patch_jump(F_GP_BUFF + i, fast[i]);
        if (ok[F_MEMORY]) g_memory_orig = (memory_fn)patch_jump(F_MEMORY, (void*)fast_memory);
        static void* const co[3] = {co_teleport, co_i32, co_u32};
        for (int i = 0; i < 3; i++)
            if (ok[F_CO_TELEPORT + i]) g_co_orig[i] = (champion_out_fn)patch_jump(F_CO_TELEPORT + i, co[i]);
    }
    text_writable_end();
    if (!getenv("TURBO_NO_MEMO")) install_memo();
    atexit(report);
}
