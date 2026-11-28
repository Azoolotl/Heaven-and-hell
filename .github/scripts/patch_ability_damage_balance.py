#!/usr/bin/env python3
"""Balance Heaven & Hell abilities against high-tier armour for v0.7.1-dev."""
import sys
from pathlib import Path

root = Path(sys.argv[1])

def read(rel):
    p = root / rel
    return p, p.read_text(encoding="utf-8")

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        if count == 0 and new in text:
            return text
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

def replace_all(text, old, new, label, minimum=1):
    count = text.count(old)
    if count < minimum:
        if old not in text and new in text:
            return text
        raise SystemExit(f"{label}: expected at least {minimum} matches, found {count}")
    return text.replace(old, new)

# Config defaults and migration: preserve deliberate server-owner custom values.
rel = "src/main/java/com/kuku/heavenhell/config/HeavenHellConfig.java"
p, s = read(rel)
s = replace_once(s,
    "public float holyBurstDamage = 9.0f, holyBurstHeal = 4.0f",
    "public float holyBurstDamage = 13.5f, holyBurstHeal = 4.0f",
    "holy burst default")
s = replace_once(s,
    "public float divineJudgementDamage = 16.0f, divineJudgementRange = 15.0f;",
    "public float divineJudgementDamage = 22.0f, divineJudgementRange = 15.0f;",
    "divine judgement default")
s = replace_once(s,
    "public float infernalBlastDamage = 10.0f, infernalBlastRadius = 6.0f",
    "public float infernalBlastDamage = 15.0f, infernalBlastRadius = 6.0f",
    "infernal blast default")
s = replace_once(s,
    "public float hellfireChainsDamage = 14.0f, hellfireChainsRange = 12.0f",
    "public float hellfireChainsDamage = 20.0f, hellfireChainsRange = 12.0f",
    "hellfire chains default")
s = replace_once(s,
    "public float zoneDamage = 5.0f, zoneAllyHeal = 2.0f",
    "public float zoneDamage = 7.5f, zoneAllyHeal = 2.0f",
    "zone damage default")
migration = """        if (Float.compare(holyBurstDamage, 9.0f) == 0) { holyBurstDamage = 13.5f; changed = true; }
        if (Float.compare(divineJudgementDamage, 16.0f) == 0) { divineJudgementDamage = 22.0f; changed = true; }
        if (Float.compare(infernalBlastDamage, 10.0f) == 0) { infernalBlastDamage = 15.0f; changed = true; }
        if (Float.compare(hellfireChainsDamage, 14.0f) == 0) { hellfireChainsDamage = 20.0f; changed = true; }
        if (Float.compare(zoneDamage, 5.0f) == 0) { zoneDamage = 7.5f; changed = true; }
"""
anchor = "        if (Float.compare(zoneDamage, 3.0f) == 0) { zoneDamage = 5.0f; changed = true; }\n"
if migration.strip() not in s:
    if anchor not in s:
        raise SystemExit("config migration anchor not found")
    s = s.replace(anchor, anchor + migration, 1)
p.write_text(s, encoding="utf-8")

# Normal abilities: partial armour bypass while retaining the caster as the damage owner.
rel = "src/main/java/com/kuku/heavenhell/gameplay/ActiveAbilityService.java"
p, s = read(rel)
s = replace_all(s, "owner.damageSources().playerAttack(owner)",
                "owner.damageSources().indirectMagic(owner, owner)", "active owner damage source")
s = replace_all(s, "player.damageSources().playerAttack(player)",
                "player.damageSources().indirectMagic(player, player)", "active player damage source")
s = replace_once(s, "zone.level.damageSources().magic()",
                 "owner.damageSources().indirectMagic(owner, owner)", "active zone damage source")
s = replace_once(s,
    "didDamage(target, owner.damageSources().indirectMagic(owner, owner), 10.0f)",
    "didDamage(target, owner.damageSources().indirectMagic(owner, owner), 14.0f)",
    "normal cataclysm meteor damage")
p.write_text(s, encoding="utf-8")

# Awakened abilities: stronger signature hits, still bounded by existing duration/cooldowns.
rel = "src/main/java/com/kuku/heavenhell/gameplay/AwakenedAbilityService.java"
p, s = read(rel)
s = replace_all(s, "player.damageSources().playerAttack(player)",
                "player.damageSources().indirectMagic(player, player)", "awakened player damage source")
s = replace_all(s, "owner.damageSources().playerAttack(owner)",
                "owner.damageSources().indirectMagic(owner, owner)", "awakened owner damage source")
s = replace_all(s, "player.damageSources().magic()",
                "player.damageSources().indirectMagic(player, player)", "awakened player magic source")
s = replace_all(s, "owner.damageSources().magic()",
                "owner.damageSources().indirectMagic(owner, owner)", "awakened owner magic source")
s = replace_once(s, "player.damageSources().indirectMagic(player, player), 8.0F",
                 "player.damageSources().indirectMagic(player, player), 10.0F", "Blood Rebirth damage")
s = replace_once(s, "scaledDamage(player, 18.0F)", "scaledDamage(player, 24.0F)", "Solar Nova damage")
s = replace_once(s, "scaledDamage(owner, 22.0F)", "scaledDamage(owner, 28.0F)", "Heaven's Verdict damage")
s = replace_once(s, "scaledDamage(owner, 19.0F)", "scaledDamage(owner, 24.0F)", "Abyssal Execution damage")
s = replace_once(s, "scaledDamage(owner, 14.0F)", "scaledDamage(owner, 18.0F)", "Hellstorm damage")
s = replace_all(s, "scaledDamage(owner, 7.0F)", "scaledDamage(owner, 8.5F)",
                "awakened zone pulse damage", minimum=2)
s = replace_once(s, "scaledDamage(owner, 12.0F)", "scaledDamage(owner, 16.0F)", "Apocalypse meteor damage")
p.write_text(s, encoding="utf-8")

# Example config documents the new defaults.
rel = "config/heavenhell.example.json"
p, s = read(rel)
for old, new, label in [
    ('"holyBurstDamage": 9.0', '"holyBurstDamage": 13.5', "example holy burst"),
    ('"divineJudgementDamage": 16.0', '"divineJudgementDamage": 22.0', "example judgement"),
    ('"infernalBlastDamage": 10.0', '"infernalBlastDamage": 15.0', "example infernal blast"),
    ('"hellfireChainsDamage": 14.0', '"hellfireChainsDamage": 20.0', "example chains"),
    ('"zoneDamage": 5.0', '"zoneDamage": 7.5', "example zone"),
]:
    s = replace_once(s, old, new, label)
p.write_text(s, encoding="utf-8")

# Release version is intentionally advanced for the balance build.
rel = "gradle.properties"
p, s = read(rel)
s = replace_once(s, "mod_version=0.7.0-dev", "mod_version=0.7.1-dev", "mod version")
p.write_text(s, encoding="utf-8")

print("Applied v0.7.1-dev armour-aware ability balance.")
