#!/usr/bin/env python3
"""Compatibility fixes for Sovereigns against the 1.21.11 mappings."""
from pathlib import Path
import sys

root = Path(sys.argv[1])

def edit(rel, replacements):
    path = root / rel
    source = path.read_text(encoding="utf-8")
    for old, new, label, expected in replacements:
        count = source.count(old)
        if count != expected:
            if count == 0 and new in source:
                continue
            raise SystemExit(f"{label}: expected {expected} matches, found {count}")
        source = source.replace(old, new)
    path.write_text(source, encoding="utf-8")

weapon = "src/main/java/com/kuku/heavenhell/gameplay/SovereignWeaponService.java"
edit(weapon, [
    ("import net.minecraft.core.particles.ParticleTypes;\n",
     "import net.minecraft.core.particles.ParticleTypes;\nimport net.minecraft.core.registries.BuiltInRegistries;\n",
     "item registry import", 1),
    ("getCooldowns().isOnCooldown(item)",
     "getCooldowns().isOnCooldown(BuiltInRegistries.ITEM.getKey(item))",
     "cooldown lookup key", 1),
    ("ServerLevel level = serverPlayer.serverLevel();",
     "ServerLevel level = (ServerLevel) serverPlayer.level();",
     "server player level accessor", 1),
    ("getCooldowns().addCooldown(item, cooldown)",
     "getCooldowns().addCooldown(BuiltInRegistries.ITEM.getKey(item), cooldown)",
     "cooldown insertion key", 1),
    ("impact.owner.serverLevel() != impact.level",
     "impact.owner.level() != impact.level",
     "pending impact dimension check", 1),
    ("this.level = owner.serverLevel();",
     "this.level = (ServerLevel) owner.level();",
     "pending impact level capture", 1),
    ("impact.level.sendParticles(impact.holy ? ParticleTypes.FLASH : ParticleTypes.EXPLOSION,",
     "impact.level.sendParticles(ParticleTypes.EXPLOSION,",
     "weapon impact particle option", 1),
])

boss = "src/main/java/com/kuku/heavenhell/gameplay/SovereignBossService.java"
edit(boss, [
    ("boss.moveTo(position.x, position.y, position.z, level.random.nextFloat() * 360.0f, 0.0f);",
     "boss.setPos(position.x, position.y, position.z);",
     "boss positioning method", 1),
    ("impact.level.sendParticles(impact.holy ? ParticleTypes.FLASH : ParticleTypes.EXPLOSION,",
     "impact.level.sendParticles(ParticleTypes.EXPLOSION,",
     "boss impact particle option", 1),
])
print("Applied Sovereigns 1.21.11 compatibility fixes.")
