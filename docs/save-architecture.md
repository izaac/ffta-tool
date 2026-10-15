# FFTA Save Architecture & Wear-Leveling Internals

Technical reference for *Final Fantasy Tactics Advance* (GBA) Flash 64K / 128K save storage, wear-leveling headers, and memory structures.

---

## 1. Flash Wear-Leveling System

FFTA uses a sector-based wear-leveling system across Flash memory to extend hardware lifespan.

- **Sector Size**: 4096 bytes (`0x1000`).
- **Save Slots**: 2 logical save slots.
- **Magic Signature**: The first 8 bytes of every valid header sector must equal ASCII `"44444444"` (`0x3434343434343434`).
- **Active Slot Selection**: The game scans sector headers for the magic bytes. If multiple valid sectors exist for a slot, the one with the highest 32-bit sequence counter is loaded.

### Header Sector Layout (Sector 0)

| Offset | Size | Type | Description |
| --- | --- | --- | --- |
| `0x00..0x08` | 8 B | ASCII | Magic identifier (`"44444444"`) |
| `0x08..0x0C` | 4 B | uint32 | Wear-leveling sequence counter (little-endian) |
| `0x0C..0x10` | 4 B | uint32 | Sector-chain CRC32 checksum |
| `0x10` | 1 B | uint8 | Slot identifier (0 = Slot 1, 1 = Slot 2) |
| `0x12..0x16` | 4 B | bytes | Physical sector allocation chain |
| `0x76..0x78` | 2 B | uint16 | Cleared missions counter |
| `0x80..0x1940` | 4224 B | struct | 24 Unit Blocks (24 × `0x108` = 6336 B spanning sectors) |

---

## 2. Unit Data Structure (`0x108` Bytes)

Every clan member occupies exactly 264 (`0x108`) bytes in the active sector chain:

| Offset | Size | Type | Description |
| --- | --- | --- | --- |
| `0x00..0x02` | 2 B | uint16 | Recruit Name ID (maps into ROM string table, 0..724) |
| `0x04` | 1 B | uint8 | Special Character Flag (1 = Standard recruit, 2 = Marche, 8 = Montblanc) |
| `0x05` | 1 B | uint8 | Sprite / Job Animation index (Job ID 2 = Soldier; avoid `0x01` prologue sprite bug) |
| `0x06` | 1 B | uint8 | Race ID (1 = Hume, 2 = Bangaa, 3 = Nu Mou, 4 = Viera, 5 = Moogle) |
| `0x07` | 1 B | uint8 | Primary Job ID |
| `0x08` | 1 B | uint8 | Secondary Job ID |
| `0x09` | 1 B | uint8 | Unit Level (1..50; 0 indicates an empty unit slot) |
| `0x18..0x20` | 8 B | 4 × uint16 | Cur HP, Max HP, Cur MP, Max MP |
| `0x20..0x28` | 8 B | 4 × uint16 | Weapon Attack, Weapon Defense, Magic Power, Magic Resistance |
| `0x28` | 1 B | uint8 | Status Flags (Bit 3: `0x08` = In Jail) |
| `0x2A..0x34` | 10 B | 5 × uint16 | Equipped Item IDs (Right Hand, Left Hand, Head, Body, Accessory) |
| `0x34` | 1 B | uint8 | Race ability table base index |
| `0x35` | 1 B | uint8 | Primary A-Ability Set ID |
| `0x36` | 1 B | uint8 | Secondary A-Ability Set ID (must differ from Primary) |
| `0x3A` | 1 B | uint8 | Reaction Ability ID |
| `0x3B` | 1 B | uint8 | Support Ability ID |
| `0x3C` | 1 B | uint8 | Combo Ability ID |
| `0x41..0x90` | N Bytes | uint8 | Ability Mastery Bitfields (`0xE4` = Mastered) |
| `0xD2..0xD4` | 2 B | uint16 | Base Speed stat |
| `0xD6` | 1 B | uint8 | Stat growth fractional counter |
| `0xF1..0x106` | 21 B | bytes | Job unlock requirement bitmask cache |
| `0x101` | 1 B | uint8 | Jail remaining battle sentence counter |
| `0x102` | 1 B | uint8 | Red cards counter |
| `0x103` | 1 B | uint8 | Yellow cards counter |
| `0x104` | 1 B | uint8 | Unit state (`0xFF` = Active / Ready) |

---

## 3. Checksum Algorithm (CRC32)

Save validity is guarded by a standard CRC32 computed across the physical sector chain specified in `hdr[0x12:0x16]`:

- Before hashing, the 4 checksum bytes at `0x0C..0x10` are treated as zero.
- If the computed CRC does not match `hdr[0x0C:0x10]`, the game rejects the save sector as corrupt and attempts fallback to older sectors.

---

## 4. Monster Bank Storage Structure (Sector 2)

Cyril's Monster Bank stores captured creatures across 20 fixed pens in Sector 2 starting at offset `0x0E78` (save buffer address `0x2E78`, RAM address `0x02002E78`). Each pen occupies exactly 16 (`0x10`) bytes (320 bytes total for all 20 pens):

| Pen Index | Monster Species | Family |
| --- | --- | --- |
| 0 | Goblin | Goblinkind |
| 1 | Red Cap | Goblinkind |
| 2 | Jelly | Flankind |
| 3 | Ice Flan | Flankind |
| 4 | Cream | Flankind |
| 5 | Bomb | Bombkind |
| 6 | Grenade | Bombkind |
| 7 | Icedrake | Dragonkind |
| 8 | Firewyrm | Dragonkind |
| 9 | Thundrake | Dragonkind |
| 10 | Lamia | Lamiakind |
| 11 | Lilith | Lamiakind |
| 12 | Antlion | Bugaboo / Antlionkind |
| 13 | Jawbreaker | Bugaboo / Antlionkind |
| 14 | Red Panther | Pantherkind |
| 15 | Coeurl | Pantherkind |
| 16 | Malboro | Malborokind |
| 17 | Big Malboro | Malborokind |
| 18 | Floateye | Ahrimankind |
| 19 | Ahriman | Ahrimankind |

### Monster Record Layout (16 Bytes)

| Offset | Size | Type | Description |
| --- | --- | --- | --- |
| `0x00..0x02` | 2 B | uint16 | Recruit Name ID (maps into ROM recruit name table) |
| `0x02..0x04` | 2 B | uint16 | Status flags (`0x0856` marks specimen captured & active) |
| `0x04` | 1 B | uint8 | Specimen active flag (`0x01` = Active) |
| `0x05` | 1 B | uint8 | Specimen Level (1..99) |
| `0x06` | 1 B | uint8 | Reserved / padding (`0x00`) |
| `0x07` | 1 B | uint8 | Affection level (0..100; 100 grants 100% Morpher stat transfer) |
| `0x08..0x10` | 8 B | bitstream | Six packed 10-bit combat stats (HP, MP, W-Atk, W-Def, M-Pow, M-Res) |

### Morpher In-Battle Transformation Check

When a Morpher executes the Morph command in combat, the battle engine inspects the candidate pens for that monster family at `0x02002E78 + pen * 16`. If the first 4 bytes of all candidate pens evaluate to zero (`0x00000000`), the Morph command for that creature family is disabled and greyed out. Populating the pens enables all Morph transformations immediately.
