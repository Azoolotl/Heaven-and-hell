from pathlib import Path
import sys

project = Path(sys.argv[1] if len(sys.argv) > 1 else "project/heaven-hell-fabric")
source = project / "src/main/java/com/kuku/heavenhell"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(
            f"Patch safety check failed for {path}: expected {expected} occurrence(s), found {count}: {old[:140]!r}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


# Angel regeneration: exactly half a health point every 20 server ticks (one second).
passives = source / "gameplay/PassiveAbilityService.java"
replace_exact(
    passives,
    """        boolean passivePulse = tickCounter % interval == 0;
        boolean fearPulse = tickCounter % 40 == 0;
        boolean dreadPulse = tickCounter % dreadInterval == 0;
        if (!passivePulse && !fearPulse && !dreadPulse) return;
        long worldTime = server.overworld().getGameTime();
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            tickPlayer(player, worldTime, passivePulse, fearPulse, dreadPulse);
        }
""",
    """        boolean passivePulse = tickCounter % interval == 0;
        boolean fearPulse = tickCounter % 40 == 0;
        boolean dreadPulse = tickCounter % dreadInterval == 0;
        boolean angelHealPulse = tickCounter % 20 == 0;
        if (!passivePulse && !fearPulse && !dreadPulse && !angelHealPulse) return;
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            tickPlayer(player, passivePulse, fearPulse, dreadPulse, angelHealPulse);
        }
""",
)
replace_exact(
    passives,
    """    private static void tickPlayer(ServerPlayer player, long worldTime,
                                   boolean passivePulse, boolean fearPulse, boolean dreadPulse) {
""",
    """    private static void tickPlayer(ServerPlayer player, boolean passivePulse,
                                   boolean fearPulse, boolean dreadPulse, boolean angelHealPulse) {
""",
)
replace_exact(
    passives,
    """            if (passivePulse && HeavenHell.CONFIG.angelBlessingEnabled && worldTime - data.lastDivineBlessingGameTime
                    >= HeavenHell.CONFIG.angelBlessingIntervalSeconds * 20L) {
                data.lastDivineBlessingGameTime = worldTime;
                player.heal(HeavenHell.CONFIG.angelBlessingHeal);
                // The timestamp is persisted on disconnect/server shutdown; avoid forcing
                // a full-world JSON rewrite on every ten-second passive pulse.
            }
""",
    """            if (angelHealPulse && HeavenHell.CONFIG.angelBlessingEnabled) {
                player.heal(0.5f);
            }
""",
)

# Keep the shipped defaults and example config consistent with the fixed passive.
config = source / "config/HeavenHellConfig.java"
replace_exact(config, "    public float angelBlessingHeal = 1.0f;\n    public int angelBlessingIntervalSeconds = 10;\n",
    "    public float angelBlessingHeal = 0.5f;\n    public int angelBlessingIntervalSeconds = 1;\n")
example = project / "config/heavenhell.example.json"
replace_exact(example, '  "angelBlessingHeal": 1.0,\n  "angelBlessingIntervalSeconds": 10,',
    '  "angelBlessingHeal": 0.5,\n  "angelBlessingIntervalSeconds": 1,')

# Add projectiles to the ability service's server-owned state and clear them on player reset/disconnect.
abilities = source / "gameplay/ActiveAbilityService.java"
replace_exact(
    abilities,
    "    private static final List<PendingMeteor> METEORS = new ArrayList<>();\n",
    "    private static final List<PendingMeteor> METEORS = new ArrayList<>();\n"
    "    private static final List<PendingProjectile> PROJECTILES = new ArrayList<>();\n",
)
replace_exact(
    abilities,
    "        METEORS.removeIf(meteor -> meteor.owner.equals(playerId));\n",
    "        METEORS.removeIf(meteor -> meteor.owner.equals(playerId));\n"
    "        PROJECTILES.removeIf(projectile -> projectile.owner.equals(playerId));\n",
    expected=2,
)

replace_exact(
    abilities,
    """    private static boolean holyBurst(ServerPlayer player) {
        ServerLevel level = player.level();
        double radius = HeavenHell.CONFIG.holyBurstRadius;
        level.sendParticles(ParticleTypes.END_ROD, player.getX(), player.getY() + 0.8, player.getZ(),
                50, radius / 2.0, 0.35, radius / 2.0, 0.12);
        level.sendParticles(ColorParticleOption.create(ParticleTypes.FLASH, 0xFFFFFF), player.getX(), player.getY() + 1.0, player.getZ(), 1, 0, 0, 0, 0);
        level.playSound(null, player.blockPosition(), AbilitySounds.HOLY_BURST, SoundSource.PLAYERS, 1.0f, 1.0f);
        player.heal(HeavenHell.CONFIG.holyBurstHeal);
        level.sendParticles(ParticleTypes.HEART, player.getX(), player.getY() + 1.0, player.getZ(), 4, 0.35, 0.4, 0.35, 0.02);
        for (LivingEntity target : nearbyLiving(player, radius)) {
            if (isEnemy(player, target)) {
                target.hurt(player.damageSources().playerAttack(player), HeavenHell.CONFIG.holyBurstDamage);
                pushAway(player, target, HeavenHell.CONFIG.holyBurstKnockback);
            } else if (isAllyPlayer(player, target)) {
                target.heal(HeavenHell.CONFIG.holyBurstHeal);
                level.sendParticles(ParticleTypes.HEART, target.getX(), target.getY() + 1.0, target.getZ(), 4, 0.35, 0.4, 0.35, 0.02);
            }
        }
        return true;
    }
""",
    """    private static boolean holyBurst(ServerPlayer player) {
        launchAbilityProjectile(player, Race.ANGEL);
        ServerLevel level = player.level();
        Vec3 muzzle = player.getEyePosition().add(player.getLookAngle().scale(0.65));
        level.sendParticles(ParticleTypes.END_ROD, muzzle.x, muzzle.y, muzzle.z, 8,
                0.12, 0.12, 0.12, 0.025);
        level.sendParticles(ColorParticleOption.create(ParticleTypes.FLASH, 0xFFFFFF),
                muzzle.x, muzzle.y, muzzle.z, 1, 0, 0, 0, 0);
        return true;
    }
""",
)

replace_exact(
    abilities,
    """    private static boolean infernalBlast(ServerPlayer player) {
        ServerLevel level = player.level();
        double radius = HeavenHell.CONFIG.infernalBlastRadius;
        level.playSound(null, player.blockPosition(), AbilitySounds.INFERNAL_BLAST, SoundSource.PLAYERS, 1.0f, 1.0f);
        level.sendParticles(ParticleTypes.FLAME, player.getX(), player.getY() + 0.6, player.getZ(), 70, radius / 2.0, 0.35, radius / 2.0, 0.1);
        level.sendParticles(ParticleTypes.EXPLOSION, player.getX(), player.getY() + 0.3, player.getZ(), 1, 0, 0, 0, 0);
        for (LivingEntity target : nearbyLiving(player, radius)) {
            if (isEnemy(player, target)) {
                target.hurt(player.damageSources().playerAttack(player), HeavenHell.CONFIG.infernalBlastDamage);
                target.igniteForSeconds(HeavenHell.CONFIG.infernalBlastFireSeconds);
                pushAway(player, target, HeavenHell.CONFIG.infernalBlastKnockback);
            }
        }
        destroyTerrainCrater(player, HeavenHell.CONFIG.infernalBlastTerrainRadius,
                HeavenHell.CONFIG.infernalBlastTerrainDepth, 36);
        return true;
    }
""",
    """    private static boolean infernalBlast(ServerPlayer player) {
        launchAbilityProjectile(player, Race.DEMON);
        ServerLevel level = player.level();
        Vec3 muzzle = player.getEyePosition().add(player.getLookAngle().scale(0.65));
        level.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, muzzle.x, muzzle.y, muzzle.z, 8,
                0.12, 0.12, 0.12, 0.025);
        level.sendParticles(ParticleTypes.FLAME, muzzle.x, muzzle.y, muzzle.z, 5,
                0.10, 0.10, 0.10, 0.02);
        return true;
    }
""",
)

# Keep the old caster-centered crater helper, and add impact-centered crater destruction for the projectile.
replace_exact(
    abilities,
    """    private static void destroyTerrainCrater(ServerPlayer owner, int radius, int depth, int maxBlocks) {
        if (!HeavenHell.CONFIG.terrainDestructionEnabled) return;
        ServerLevel level = owner.level();
        int centerX = owner.blockPosition().getX();
        int centerY = owner.blockPosition().getY();
        int centerZ = owner.blockPosition().getZ();
""",
    """    private static void destroyTerrainCrater(ServerPlayer owner, int radius, int depth, int maxBlocks) {
        destroyTerrainCrater(owner, owner.position(), radius, depth, maxBlocks);
    }

    private static void destroyTerrainCrater(ServerPlayer owner, Vec3 center, int radius, int depth, int maxBlocks) {
        if (!HeavenHell.CONFIG.terrainDestructionEnabled) return;
        ServerLevel level = owner.level();
        int centerX = net.minecraft.util.Mth.floor(center.x);
        int centerY = net.minecraft.util.Mth.floor(center.y);
        int centerZ = net.minecraft.util.Mth.floor(center.z);
""",
)

projectile_methods = """    private static void launchAbilityProjectile(ServerPlayer owner, Race race) {
        Vec3 direction = owner.getLookAngle().normalize();
        Vec3 start = owner.getEyePosition().add(direction.scale(0.65));
        PROJECTILES.add(new PendingProjectile(owner.getUUID(), race, owner.level(), start,
                direction.scale(1.25), 48));
    }

    private static void tickProjectiles(MinecraftServer server) {
        Iterator<PendingProjectile> iterator = PROJECTILES.iterator();
        while (iterator.hasNext()) {
            PendingProjectile projectile = iterator.next();
            ServerPlayer owner = server.getPlayerList().getPlayer(projectile.owner);
            PlayerData ownerData = owner == null ? null : HeavenHell.DATA.get(owner.getUUID());
            if (owner == null || !owner.isAlive() || owner.level() != projectile.level
                    || ownerData == null || ownerData.race != projectile.race || ownerData.isPowerless()) {
                iterator.remove();
                continue;
            }

            Vec3 start = projectile.position;
            Vec3 end = start.add(projectile.velocity);
            HitResult blockHit = projectile.level.clip(new ClipContext(start, end,
                    ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, owner));
            Vec3 blockPoint = blockHit.getType() == HitResult.Type.MISS ? null : blockHit.getLocation();
            LivingEntity entityHit = findProjectileEntityHit(owner, projectile.level, start, end);
            Vec3 entityPoint = entityHit == null
                    ? null : entityHit.getBoundingBox().inflate(0.25).clip(start, end).orElse(entityHit.position());

            Vec3 impact = null;
            if (entityPoint != null && (blockPoint == null
                    || start.distanceToSqr(entityPoint) < start.distanceToSqr(blockPoint))) {
                impact = entityPoint;
            } else if (blockPoint != null) {
                impact = blockPoint;
            }

            if (impact != null) {
                detonateAbilityProjectile(owner, projectile, impact);
                iterator.remove();
                continue;
            }

            projectile.position = end;
            projectile.ticksLeft--;
            if (projectile.race == Race.ANGEL) {
                projectile.level.sendParticles(ParticleTypes.END_ROD, end.x, end.y, end.z,
                        3, 0.035, 0.035, 0.035, 0.01);
                projectile.level.sendParticles(ParticleTypes.ELECTRIC_SPARK, end.x, end.y, end.z,
                        1, 0.025, 0.025, 0.025, 0.005);
            } else {
                projectile.level.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, end.x, end.y, end.z,
                        4, 0.045, 0.045, 0.045, 0.012);
                projectile.level.sendParticles(ParticleTypes.SMOKE, end.x, end.y, end.z,
                        1, 0.025, 0.025, 0.025, 0.005);
            }
            if (projectile.ticksLeft <= 0) iterator.remove();
        }
    }

    private static LivingEntity findProjectileEntityHit(ServerPlayer owner, ServerLevel level,
                                                          Vec3 start, Vec3 end) {
        AABB search = new AABB(start, end).inflate(0.35);
        LivingEntity closest = null;
        double closestDistance = Double.MAX_VALUE;
        for (LivingEntity candidate : level.getEntitiesOfClass(LivingEntity.class, search,
                entity -> entity != owner && entity.isAlive() && !(entity instanceof ArmorStand))) {
            Vec3 intercept = candidate.getBoundingBox().inflate(0.25).clip(start, end).orElse(null);
            if (intercept == null) continue;
            double distance = start.distanceToSqr(intercept);
            if (distance < closestDistance) {
                closest = candidate;
                closestDistance = distance;
            }
        }
        return closest;
    }

    private static void detonateAbilityProjectile(ServerPlayer owner, PendingProjectile projectile, Vec3 impact) {
        if (projectile.race == Race.ANGEL) {
            impactHolyBurst(owner, projectile.level, impact);
        } else {
            impactInfernalBlast(owner, projectile.level, impact);
        }
    }

    private static List<LivingEntity> livingAround(ServerPlayer owner, ServerLevel level, Vec3 center, double radius) {
        AABB area = new AABB(center.x - radius, center.y - radius, center.z - radius,
                center.x + radius, center.y + radius, center.z + radius);
        return level.getEntitiesOfClass(LivingEntity.class, area,
                entity -> entity != owner && entity.isAlive() && !(entity instanceof ArmorStand)
                        && entity.position().distanceToSqr(center) <= radius * radius);
    }

    private static void impactHolyBurst(ServerPlayer owner, ServerLevel level, Vec3 center) {
        double radius = HeavenHell.CONFIG.holyBurstRadius;
        level.sendParticles(ParticleTypes.EXPLOSION_EMITTER, center.x, center.y, center.z, 1, 0, 0, 0, 0);
        level.sendParticles(ParticleTypes.END_ROD, center.x, center.y, center.z,
                54, radius / 2.0, 0.45, radius / 2.0, 0.12);
        level.sendParticles(ColorParticleOption.create(ParticleTypes.FLASH, 0xFFFFFF),
                center.x, center.y, center.z, 1, 0, 0, 0, 0);
        level.playSound(null, new BlockPos(net.minecraft.util.Mth.floor(center.x),
                        net.minecraft.util.Mth.floor(center.y), net.minecraft.util.Mth.floor(center.z)),
                AbilitySounds.HOLY_BURST, SoundSource.PLAYERS, 1.0f, 1.0f);
        owner.heal(HeavenHell.CONFIG.holyBurstHeal);
        level.sendParticles(ParticleTypes.HEART, owner.getX(), owner.getY() + 1.0, owner.getZ(),
                4, 0.35, 0.4, 0.35, 0.02);

        for (LivingEntity target : livingAround(owner, level, center, radius)) {
            if (isEnemy(owner, target)) {
                target.hurt(owner.damageSources().playerAttack(owner), HeavenHell.CONFIG.holyBurstDamage);
                pushAwayFromPoint(target, center, HeavenHell.CONFIG.holyBurstKnockback);
            } else if (isAllyPlayer(owner, target)) {
                target.heal(HeavenHell.CONFIG.holyBurstHeal);
                level.sendParticles(ParticleTypes.HEART, target.getX(), target.getY() + 1.0,
                        target.getZ(), 4, 0.35, 0.4, 0.35, 0.02);
            }
        }
    }

    private static void impactInfernalBlast(ServerPlayer owner, ServerLevel level, Vec3 center) {
        double radius = HeavenHell.CONFIG.infernalBlastRadius;
        level.sendParticles(ParticleTypes.EXPLOSION_EMITTER, center.x, center.y, center.z, 1, 0, 0, 0, 0);
        level.sendParticles(ParticleTypes.FLAME, center.x, center.y, center.z,
                70, radius / 2.0, 0.45, radius / 2.0, 0.10);
        level.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, center.x, center.y, center.z,
                28, radius / 2.3, 0.35, radius / 2.3, 0.08);
        level.sendParticles(ParticleTypes.SMOKE, center.x, center.y + 0.2, center.z,
                20, radius / 2.4, 0.3, radius / 2.4, 0.04);
        level.playSound(null, new BlockPos(net.minecraft.util.Mth.floor(center.x),
                        net.minecraft.util.Mth.floor(center.y), net.minecraft.util.Mth.floor(center.z)),
                AbilitySounds.INFERNAL_BLAST, SoundSource.PLAYERS, 1.0f, 1.0f);

        for (LivingEntity target : livingAround(owner, level, center, radius)) {
            if (isEnemy(owner, target)) {
                target.hurt(owner.damageSources().playerAttack(owner), HeavenHell.CONFIG.infernalBlastDamage);
                target.igniteForSeconds(HeavenHell.CONFIG.infernalBlastFireSeconds);
                pushAwayFromPoint(target, center, HeavenHell.CONFIG.infernalBlastKnockback);
            }
        }
        destroyTerrainCrater(owner, center, HeavenHell.CONFIG.infernalBlastTerrainRadius,
                HeavenHell.CONFIG.infernalBlastTerrainDepth, 36);
    }

    private static void pushAwayFromPoint(LivingEntity target, Vec3 center, double strength) {
        Vec3 away = target.position().subtract(center);
        if (away.lengthSqr() < 0.0001) away = new Vec3(0, 0, 1);
        away = away.normalize();
        target.setDeltaMovement(target.getDeltaMovement().add(away.x * strength, 0.25, away.z * strength));
        target.hurtMarked = true;
    }

"""
replace_exact(abilities, "    private static boolean divineJudgement(ServerPlayer player) {\n",
    projectile_methods + "    private static boolean divineJudgement(ServerPlayer player) {\n")

replace_exact(
    abilities,
    """    private static void tick(MinecraftServer server) {
        Iterator<PendingJudgement> judgementIterator = JUDGEMENTS.iterator();
""",
    """    private static void tick(MinecraftServer server) {
        tickProjectiles(server);

        Iterator<PendingJudgement> judgementIterator = JUDGEMENTS.iterator();
""",
)

replace_exact(
    abilities,
    "    private static final class PendingJudgement {\n",
    """    private static final class PendingProjectile {
        final UUID owner;
        final Race race;
        final ServerLevel level;
        final Vec3 velocity;
        Vec3 position;
        int ticksLeft;

        PendingProjectile(UUID owner, Race race, ServerLevel level, Vec3 position, Vec3 velocity, int ticksLeft) {
            this.owner = owner;
            this.race = race;
            this.level = level;
            this.position = position;
            this.velocity = velocity;
            this.ticksLeft = ticksLeft;
        }
    }

    private static final class PendingJudgement {
""",
)

print("Applied Angel regeneration and Angel/Demon projectile ability updates successfully.")
