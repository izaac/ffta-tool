# FFTA Clan Strategy & Equipment Metagame Guide

Strategic and tactical rationale behind the default builds in `builds.toml` and race fleets.

---

## 1. The Core Metagame Rule: "We Don't Learn, We Know Everything"

Standard internet guides and vanilla playthroughs prioritize equipment that teaches abilities (e.g. equipping Materia Blade for Double Sword, Flamberge for Strikebombs, or Spring Staff for healing).

In our system:

- **100% Mastered Abilities**: Every injected recruit and clan unit already has 100% of abilities mastered (`0xE4` bitmask across all race ability slots).
- **Zero Skill-Learning Gear**: Low-attack gear is strictly prohibited. Units are equipped exclusively for maximum combat efficacy, high speed, and status immunities.

### Key Equipment Upgrades

| Outdated Skill Gear | Meta Combat Upgrade | Stat Difference |
| --- | --- | --- |
| **Materia Blade** (17 Atk) | **Ebon Blade** (84 Atk, Dark) | +67 WAtk |
| **Ayvuir Red** (62 Atk) | **Ebon Blade** (84 Atk, Dark) | +22 WAtk |
| **Flamberge** (35 Atk) | **Femme Fatale** (49 Atk, +2 Spd) | +14 WAtk, +2 Speed, Null Doom |
| **Spring Staff** (28 Atk) | **Dream Watcher** (43 Atk, +10 MPow, +15 MRes) | +15 WAtk, +10 MPow, +15 MRes |
| **Silver Sword** (20 Atk) | **Chirijiraden** (65 Atk) | +45 WAtk |
| **Shortbow** (19 Atk) | **Perseus Bow** (42 Atk) | +23 WAtk |

---

## 2. MP Mechanics in FFTA (GBA)

A critical distinction between *Final Fantasy Tactics Advance* (GBA) and its Nintendo DS sequel (*FFTA2*):

- **Start of Battle**: Units enter every battle with **100% maximum MP**.
- **Per-Turn Regeneration**: There is **no passive auto-MP regen** (+10 MP) in FFTA GBA. Once MP is spent, it does not regenerate automatically.
- **Sustaining MP**:
  - **Turbo MP** (Support): Doubles Magic Power at double MP cost (devastating for high-burst alpha strikes).
  - **Half MP** (Support): Cuts MP costs in half, enabling repeated Ultima or high-tier magic casting every turn.
  - **Damage > MP / Absorb MP** (Reaction): Recharges MP equal to incoming magic damage/cost.
  - **Angel Ring**: Provides Auto-Life and Dark/Zombie resistance, ensuring caster survival.

---

## 3. Race Tactical Synergy & Loadout Rationale

### Hume Fleet (Versatility & Dual Wield)

- **Blue Mage**: Dual Tulwars (+4 Speed total, 43 Atk each), Acacia Hat (+2 Speed, +20 Res), Ninja Gear (+2 Speed), Fairy Shoes (teleport mobility). Master of crowd control (Night, Roulette, Bad Breath).
- **Paladin**: Dual Excaliburs (47 Atk each, Holy element, +2 MPow, +1 Speed, +5 Evade) delivering Holy Blade strikes, Maximillian (+62 Def plate), Mindu Gem (complete status immunity), and Ninja Tabi (+2 Move).
- **Fighter**: Ebon Blade (84 Atk) with Air Render and Back Draft.
- **Thief**: Cinquedea (57 Atk, +5 Speed) paired with Concentrate (guarantees 95% Steal rate on Weapon, Armor, and Ability), Reflex (100% physical evasion), Thief Hat, Ninja Gear, Ninja Tabi, and Genji Armlets. Dual Cinquedea Double Sword variant also available for raw speed stack (+10 Speed).
- **Default Secondary**: Fighter Tech (Set 4). If primary is Fighter, falls back to Paladin Holy Blade (Set 3).

### Bangaa Fleet (Heavy Physical Dominance)

- **White Monk Gear Constraint**: White Monks **cannot equip headgear or shields** in FFTA engine rules. Equipped with Godhand (52 Atk), Ninja Gear, Ninja Tabi, Mindu Gem, and Genji Armlets.
- **Gladiator**: Ebon Blade (84 Atk) Ultima Sword striker.
- **Dragoon**: Bangaa Spike (53 Atk, +5 Def, +5 Res, 2-handed spear) for 2-tile piercing reach and Jump.
- **Defender / Templar**: Excalibur (47 Atk, Holy element, +1 Speed, +5 Evade) paired with Genji Shield (+10 Evade) and Maximillian plate.
- **Default Secondary**: White Monk Tech (Set 22: Air Render, Far Fist, Earth Render).

### Nu Mou Fleet (Devastating Magic Artistry)

- **Sage**: Sage Crosier (31 Atk, +8 MPow), Magic Robe (+10 MPow), Acacia Hat, Angel Ring. Dual-threat Bio and Giga Flare with Time Magic secondary.
- **Morpher**: Dragon Soul (36 Atk) beast form transformation with Black Robe elemental boosts.
- **Alchemist**: Scorpion Tail (42 Atk Mace) for transmuting items and Death spells.
- **Default Secondary**: Time Magic (Set 13: Haste, Quicken, Stop). If primary is Time Mage, falls back to Sage Sagacity (Set 18).

### Viera Fleet (Speed & Lethality)

- **Assassin**: Masamune 100 (65 Atk, +2 Speed), Ribbon (full female status immunity), Ninja Gear, Ninja Tabi, Genji Armlets. 200+ Speed capable of opening turns with Last Breath (KO) or Rockseal.
- **Red Mage**: Aerial Hole (43 Atk, +8 MPow, +2 Speed) paired with Doublecast and Summoning secondary.
- **Summoner**: Dream Watcher (43 Atk, +10 MPow, +15 MRes) providing the highest Magic Power staff boost for summons (Madeen, Ramuh, Shiva, Ifrit) paired with Magic Robe (+10 MPow), Ribbon, and Angel Ring.
- **Sniper**: Max's Oathbow (63 Atk) with Beso Toxico and Aim Armor.
- **Default Secondary**: Sharpshoot (Set 26). If primary is Sniper, falls back to Assassination (Set 25).

### Moogle Fleet (Utility & Long Range)

- **Gunner**: Calling Gun (43 Atk, Range 8), Thief Hat, Ninja Gear, Ninja Tabi, Angel Ring. Map-wide Stopshot and Confushot disablers.
- **Mog Knight**: Heavy plate holy tank with Ebon Blade (84 Atk), Maximillian, and Genji Shield.
- **Juggler**: Cinquedea (+5 Speed) throwing Smile (instant turn grants) and Ball/Dagger disablers.
- **Default Secondary**: Charge (Set 32). If primary is Mog Knight, falls back to Gunmanship (Set 28).

---

## 4. Anti-Duplicate Skill Guarantee

Having matching primary and secondary A-ability sets breaks unit versatility and clutters the battle command menu.

The tool strictly enforces canonical alternate pairings whenever collisions occur:

- **Hume Fighter**: Secondary automatically shifts from Fighter Tech to **Paladin (Set 3)**.
- **Bangaa White Monk**: Secondary automatically shifts from Monk Tech to **Gladiator (Set 8)**.
- **Nu Mou Time Mage**: Secondary automatically shifts from Time Magic to **Sage (Set 18)**.
- **Viera Sniper**: Secondary automatically shifts from Sharpshoot to **Assassin (Set 25)**.
- **Moogle Mog Knight**: Secondary automatically shifts from Charge to **Gunner (Set 28)**.
