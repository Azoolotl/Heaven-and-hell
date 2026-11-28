from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "src/main/java/com/kuku/heavenhell/gameplay/EvolutionService.java"
source = path.read_text(encoding="utf-8")

replacements = [
    ("""            addEffect(player, MobEffects.RESISTANCE, 60, 1);
            addEffect(player, MobEffects.REGENERATION, 60, 1);
            addEffect(player, MobEffects.SPEED, 60, 1);
            addEffect(player, MobEffects.SLOW_FALLING, 60, 0);""",
     """            addEffect(player, MobEffects.RESISTANCE, 60, 2);
            addEffect(player, MobEffects.REGENERATION, 60, 2);
            addEffect(player, MobEffects.SPEED, 60, 2);"""),
    ("""            addEffect(player, MobEffects.SPEED, 60, 1);
            addEffect(player, MobEffects.REGENERATION, 60, 0);""",
     """            addEffect(player, MobEffects.SPEED, 60, 2);
            addEffect(player, MobEffects.REGENERATION, 60, 2);"""),
]
for old, new in replacements:
    if old in source:
        source = source.replace(old, new, 1)
    elif new not in source:
        raise SystemExit("Expected Evolution passive block not found")

old_handler = """    private static void onEntityDeath(LivingEntity dead, DamageSource source) {
        if (!(dead instanceof Mob mob) || mob.isPersistenceRequired()
                || mob.getType().getCategory() != MobCategory.MONSTER || source == null) return;
        Entity responsible = AwakeningService.resolvePlayerAttacker(source);
        if (!(responsible instanceof ServerPlayer killer)) return;
        PlayerData data = HeavenHell.DATA.get(killer.getUUID());
        if (!data.evolutionQuestStarted || !data.evolutionQuestDragonBreath || data.evolutionUnlocked
                || !meetsTrialRequirements(data)) return;
        String species = BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()).toString();
        if (!data.evolutionTrialMobTypes.add(species)) return;
        data.lastUpdated = System.currentTimeMillis();
        HeavenHell.DATA.save();
        int count = data.evolutionTrialMobTypes.size();
        int required = HeavenHell.CONFIG.evolutionTrialUniqueMobKills;
        killer.displayClientMessage(Component.literal("§d✦ Evolution Trial: " + count + "/" + required
                + " unique hostile species §7(" + species + ")"), false);
        if (count >= required) completeTrial(killer, data);
    }
"""
new_handler = """    private static void onEntityDeath(LivingEntity dead, DamageSource source) {
        if (source == null) return;
        Entity responsible = AwakeningService.resolvePlayerAttacker(source);
        if (!(responsible instanceof ServerPlayer killer)) return;
        PlayerData data = HeavenHell.DATA.get(killer.getUUID());
        if (!data.evolutionQuestStarted || !data.evolutionQuestDragonBreath || data.evolutionUnlocked
                || !meetsTrialRequirements(data)) return;

        final String progressKey;
        final String progressLabel;
        if (dead instanceof ServerPlayer victim) {
            // PvP counts once per distinct opposing player, preventing repeated kill-farming.
            if (victim == killer || victim.isSpectator() || isAlly(killer, victim)) return;
            progressKey = "player:" + victim.getUUID();
            progressLabel = "enemy player";
        } else if (dead instanceof Mob mob && !mob.isPersistenceRequired()
                && mob.getType().getCategory() == MobCategory.MONSTER) {
            progressKey = BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()).toString();
            progressLabel = "hostile species";
        } else {
            return;
        }

        if (!data.evolutionTrialMobTypes.add(progressKey)) return;
        data.lastUpdated = System.currentTimeMillis();
        HeavenHell.DATA.save();
        int count = data.evolutionTrialMobTypes.size();
        int required = HeavenHell.CONFIG.evolutionTrialUniqueMobKills;
        killer.displayClientMessage(Component.literal("§d✦ Evolution Trial: " + count + "/" + required
                + " unique combat victories §7(" + progressLabel + ")"), false);
        if (count >= required) completeTrial(killer, data);
    }
"""
if old_handler in source:
    source = source.replace(old_handler, new_handler, 1)
elif new_handler not in source:
    raise SystemExit("Evolution death handler did not match expected source")
source = source.replace("Defeat five different hostile mob species.",
                        "Earn five unique combat victories against hostile mobs or enemy players.")
source = source.replace("different hostile mob species defeated. The Dragon's Breath has already been offered.",
                        "unique combat victories earned. Hostile mob species and distinct enemy players both count. The Dragon's Breath has already been offered.")
if "MobEffects.SLOW_FALLING" in source:
    raise SystemExit("Slow Falling still present in Evolution passives")
if 'progressKey = "player:" + victim.getUUID();' not in source:
    raise SystemExit("PvP progression patch missing")
path.write_text(source, encoding="utf-8")
print("Updated Evolution passives and PvP trial progression.")
