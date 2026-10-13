"""Final Fantasy Tactics Advance (GBA) Data Mappings & Constants.

Contains canonical lookup dictionaries for races, jobs, equipment IDs,
ability specifications, and memory structures used by ffta_tool.
"""

# Races
RACE_NAMES: dict[int, str] = {
    1: "Hume",
    2: "Bangaa",
    3: "Nu Mou",
    4: "Viera",
    5: "Moogle",
}

# Jobs (Hex ID -> (Job Name, Race))
JOB_NAMES: dict[int, tuple[str, str]] = {
    # Hume (0x01..0x0C)
    0x01: ("Soldier", "Hume"),
    0x02: ("Paladin", "Hume"),
    0x03: ("Paladin", "Hume"),
    0x04: ("Fighter", "Hume"),
    0x05: ("Thief", "Hume"),
    0x06: ("Ninja", "Hume"),
    0x07: ("White Mage", "Hume"),
    0x08: ("Black Mage", "Hume"),
    0x09: ("Illusionist", "Hume"),
    0x0A: ("Blue Mage", "Hume"),
    0x0B: ("Archer", "Hume"),
    0x0C: ("Hunter", "Hume"),
    # Bangaa (0x0D..0x13)
    0x0D: ("Warrior", "Bangaa"),
    0x0E: ("White Monk", "Bangaa"),
    0x0F: ("Dragoon", "Bangaa"),
    0x10: ("Gladiator", "Bangaa"),
    0x11: ("Defender", "Bangaa"),
    0x12: ("Bishop", "Bangaa"),
    0x13: ("Templar", "Bangaa"),
    # Nu Mou (0x14..0x1B)
    0x14: ("White Mage", "Nu Mou"),
    0x15: ("Black Mage", "Nu Mou"),
    0x16: ("Time Mage", "Nu Mou"),
    0x17: ("Illusionist", "Nu Mou"),
    0x18: ("Alchemist", "Nu Mou"),
    0x19: ("Beastmaster", "Nu Mou"),
    0x1A: ("Morpher", "Nu Mou"),
    0x1B: ("Sage", "Nu Mou"),
    # Viera (0x1C..0x23)
    0x1C: ("Fencer", "Viera"),
    0x1D: ("Elementalist", "Viera"),
    0x1E: ("Red Mage", "Viera"),
    0x1F: ("White Mage", "Viera"),
    0x20: ("Summoner", "Viera"),
    0x21: ("Archer", "Viera"),
    0x22: ("Assassin", "Viera"),
    0x23: ("Sniper", "Viera"),
    # Moogle (0x24..0x2B)
    0x24: ("Animist", "Moogle"),
    0x25: ("Mog Knight", "Moogle"),
    0x26: ("Gunner", "Moogle"),
    0x27: ("Thief", "Moogle"),
    0x28: ("Juggler", "Moogle"),
    0x29: ("Gadgeteer", "Moogle"),
    0x2A: ("Black Mage", "Moogle"),
    0x2B: ("Time Mage", "Moogle"),
}

# Known signature items for visualizer
KNOWN_ITEMS: dict[int, str] = {
    # Swords & Blades
    0x0001: "Shortsword",
    0x0002: "Silver Sword",
    0x0003: "Buster Sword",
    0x0004: "Burglar Sword",
    0x0005: "Gale Sword",
    0x0006: "Blood Sword",
    0x0008: "Restorer",
    0x0009: "Mythril Sword",
    0x0012: "Flametongue",
    0x001A: "Materia Blade",
    # Sabers
    0x001E: "Ayvuir Red",
    0x001F: "Ayvuir Blue",
    0x0020: "Blue Saber",
    0x0026: "Tulwar",
    # Knightswords
    0x0028: "Defender",
    0x0029: "Apocalypse",
    0x002A: "Lion Heart",
    0x002B: "Ragnarok",
    0x002F: "Excalibur",
    0x0030: "Mythril Brand",
    0x0031: "Excalibur 2",
    0x0032: "Nagrarok",
    0x0033: "Sequence",
    # Knives & Rapiers
    0x004C: "Khukuri",
    0x004E: "Scramasax",
    0x0056: "Mythril Knife",
    0x0057: "Tonberrian",
    0x0058: "Tiptaptwo",
    0x005C: "Flamberge",
    # Katanas & Ninja Blades
    0x0073: "Masamune",
    0x0076: "Masamune 100",
    # Staves & Rods
    0x0079: "White Staff",
    0x0085: "Power Staff",
    0x0086: "Dream Watcher",
    0x0087: "Rod",
    0x0088: "Firewheel Rod",
    # Maces
    0x009C: "Lotus Mace",
    0x009D: "Scorpion Tail",
    0x009E: "Zeus Mace",
    0x009F: "Mythril Mace",
    # Bows & Greatbows
    0x00A2: "Longbow",
    0x00B5: "Nike Bow",
    0x00B8: "Seventh Heaven",
    0x00CF: "Silver Bow",
    # Spears & Instruments
    0x00C2: "Partisan",
    0x00CC: "Conch Shell",
    # Knuckles
    0x00D7: "Hard Knuckles",
    0x00DB: "Kaiser Knuckles",
    # Guns
    0x00F5: "Lost Gun",
    0x00F6: "Peacemaker",
    0x00F7: "Giot Gun",
    # Shields
    0x00FD: "Bronze Shield",
    0x00FE: "Round Shield",
    0x00FF: "Opal Shield",
    0x0100: "Ice Shield",
    0x0101: "Flame Shield",
    0x0102: "Aegis Shield",
    0x0103: "Genji Shield",
    0x0104: "Sacri Shield",
    0x0105: "Shijin Shield",
    0x0106: "Chocobo Shield",
    0x0107: "La Seraphica",
    0x0108: "Reverie Shield",
    # Helmets & Headgear
    0x0109: "Bronze Helmet",
    0x010A: "Iron Helmet",
    0x010B: "Opal Helmet",
    0x010C: "Cross Helmet",
    0x010D: "Diamond Helmet",
    0x010E: "Genji Helmet",
    0x010F: "Parade Helmet",
    0x0110: "Hanya Helmet",
    0x0111: "Bangaa Helmet",
    0x0112: "Cachusha",
    0x0113: "Barette",
    0x0114: "Ribbon",
    # Hats
    0x0115: "Feather Cap",
    0x0116: "Circlet",
    0x0117: "Green Beret",
    0x0118: "Headband",
    0x0119: "Wizard Hat",
    0x011A: "Gold Hairpin",
    0x011B: "Thief Hat",
    0x011C: "Black Hat",
    0x011D: "White Hat",
    0x011E: "Acacia Hat",
    0x011F: "Tiara",
    # Armors & Vests
    0x0120: "Cuirass",
    0x0121: "Bronze Armor",
    0x0122: "Iron Armor",
    0x0123: "Platemail",
    0x0124: "Gold Armor",
    0x012F: "Leather Garb",
    0x0130: "Chain Plate",
    0x0131: "Adaman Vest",
    0x0132: "Survival Vest",
    0x0133: "Brigandine",
    0x0137: "Minerva Plate",
    0x0138: "Ninja Gear",
    0x0139: "Dark Gear",
    # Robes
    0x0143: "Hempen Robe",
    0x0147: "Blaze Robe",
    0x014B: "Black Robe",
    0x014C: "Light Robe",
    0x014D: "Lordly Robe",
    # Boots & Shoes
    0x0153: "Battle Boots",
    0x0154: "Spiked Boots",
    0x0155: "Dash Boots",
    0x015A: "Fairy Shoes",
    0x015C: "Ninja Tabi",
    # Accessories
    0x015D: "Gauntlets",
    0x0163: "Fortune Ring",
    0x0165: "Angel Ring",
    0x0169: "Mindu Gem",
}

# Race ability counts starting at unit + 0x41
RACE_ABILITY_SPECS: dict[int, tuple[int, int, bool]] = {
    1: (140, 26, False),  # Hume: count, blue_magic, morpher
    2: (76, 0, False),  # Bangaa
    3: (94, 0, True),  # Nu Mou: + morpher
    4: (84, 0, False),  # Viera
    5: (87, 0, False),  # Moogle
}

# Cache byte array at unit + 0xF1..0x106 used by the Job change menu
RACE_JOB_COUNTERS: dict[int, bytes] = {
    1: bytes.fromhex("ff 0c 00 00 00 02 05 02 02 05 06 01 02 03 fc 00 02 00 00 02 00"),
    2: bytes.fromhex("0e 02 00 00 00 0a 07 01 00 00 09 01 02 02 fd 00 01 00 00 03 00"),
    3: bytes.fromhex("6b 18 00 00 00 07 02 01 00 00 0a 01 02 04 fb 00 01 00 00 01 00"),
    4: bytes.fromhex("ff 10 00 00 00 07 07 03 00 00 0b 01 02 04 fb 00 02 00 00 00 00"),
    5: bytes.fromhex("37 07 00 00 00 0a 02 01 04 01 07 01 02 02 fd 00 01 00 00 05 00"),
}

EQUIPMENT_IDS: list[int] = list(range(1, 0x16A))
CONSUMABLE_IDS: list[int] = list(range(0x16A, 0x178))

__all__ = [
    "CONSUMABLE_IDS",
    "EQUIPMENT_IDS",
    "JOB_NAMES",
    "KNOWN_ITEMS",
    "RACE_ABILITY_SPECS",
    "RACE_JOB_COUNTERS",
    "RACE_NAMES",
]
