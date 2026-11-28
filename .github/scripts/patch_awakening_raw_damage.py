#!/usr/bin/env python3
"""Make Awakening progression use pre-armor damage and remove obsolete health snapshots."""
import sys
from pathlib import Path

root = Path(sys.argv[1])
path = root / "src/main/java/com/kuku/heavenhell/gameplay/AwakeningService.java"
source = path.read_text(encoding="utf-8")
old = """    /** Uses health actually lost, not attempted/pre-mitigation damage. */
    public static void onLivingEntityDamaged(LivingEntity victim, DamageSource source,
                                              float baseDamageTaken, float damageTaken, boolean blocked) {
        Float before = victim == null ? null : HEALTH_BEFORE_DAMAGE.remove(victim);
        if (blocked || victim == null || source == null || before == null) return;
        float actualHealthLost = Math.max(0.0F, before - victim.getHealth());
        if (!Float.isFinite(actualHealthLost) || actualHealthLost <= 0.0F || victim instanceof ArmorStand) return;

        Entity attacker = resolveAttacker(source);
        if (attacker instanceof ServerPlayer playerAttacker
                && isEligible(HeavenHell.DATA.get(playerAttacker.getUUID()))
                && isEnemy(playerAttacker, victim)) {
            addDamageProgress(playerAttacker, actualHealthLost, true, victim instanceof ServerPlayer);
        }
        if (victim instanceof ServerPlayer defender && defender.isAlive()
                && isEligible(HeavenHell.DATA.get(defender.getUUID()))
                && isValidCombatSource(attacker, defender)) {
            addDamageProgress(defender, actualHealthLost, false, attacker instanceof ServerPlayer);
        }
    }
"""
new = """    /** Uses Fabric's pre-armor base damage, so armor does not reduce Awakening progress. */
    public static void onLivingEntityDamaged(LivingEntity victim, DamageSource source,
                                              float baseDamageTaken, float damageTaken, boolean blocked) {
        if (blocked || victim == null || source == null || victim instanceof ArmorStand) return;
        // Fabric AFTER_DAMAGE provides baseDamageTaken before armor and enchantment reduction.
        // Shield-blocked hits are excluded by the blocked flag above.
        float progressDamage = Math.max(0.0F, baseDamageTaken);
        if (!Float.isFinite(progressDamage) || progressDamage <= 0.0F) return;

        Entity attacker = resolveAttacker(source);
        if (attacker instanceof ServerPlayer playerAttacker
                && isEligible(HeavenHell.DATA.get(playerAttacker.getUUID()))
                && isEnemy(playerAttacker, victim)) {
            addDamageProgress(playerAttacker, progressDamage, true, victim instanceof ServerPlayer);
        }
        if (victim instanceof ServerPlayer defender
                && isEligible(HeavenHell.DATA.get(defender.getUUID()))
                && isValidCombatSource(attacker, defender)) {
            addDamageProgress(defender, progressDamage, false, attacker instanceof ServerPlayer);
        }
    }
"""
if old not in source:
    raise SystemExit("Expected original Awakening damage handler not found; refusing unsafe patch")
source = source.replace(old, new)

# These snapshots were only used by the old post-armor health-difference calculation.
source = source.replace(
    "    private static final Map<LivingEntity, Float> HEALTH_BEFORE_DAMAGE = new java.util.WeakHashMap<>();\n", ""
)
source = source.replace("            HEALTH_BEFORE_DAMAGE.put(entity, entity.getHealth());\n", "")
source = source.replace("        HEALTH_BEFORE_DAMAGE.remove(victim);\n", "")
source = source.replace("        if (dead != null) HEALTH_BEFORE_DAMAGE.remove(dead);\n", "")
source = source.replace("        HEALTH_BEFORE_DAMAGE.remove(player);\n", "")
if "HEALTH_BEFORE_DAMAGE" in source:
    raise SystemExit("Obsolete health snapshot references remain; refusing incomplete cleanup")

path.write_text(source, encoding="utf-8")
print("Patched Awakening progress to use raw pre-armor damage")
