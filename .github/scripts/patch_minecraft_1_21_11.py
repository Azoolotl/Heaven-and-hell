from pathlib import Path
import sys

project = Path(sys.argv[1] if len(sys.argv) > 1 else "project/heaven-hell-fabric")
source = project / "src/main/java/com/kuku/heavenhell"

def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"Patch safety check failed for {path}: expected {expected} occurrence(s), found {count}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")

# Minecraft 1.21.11 uses PermissionCheck providers instead of integer permission levels.
replace_exact(
    source / "command/HeavenHellCommands.java",
    ".requires(s -> s.hasPermission(2))",
    ".requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))",
    expected=7,
)

# ServerPlayer.level() returns ServerLevel in 1.21.11; the server is accessed from that level.
replace_exact(
    source / "HeavenHell.java",
    "StatusSync.removeFromClients(newPlayer.getServer(), oldPlayer.getId());",
    "StatusSync.removeFromClients(newPlayer.level().getServer(), oldPlayer.getId());",
)

status_sync = source / "network/StatusSync.java"
replace_exact(status_sync, "viewer.getServer()", "viewer.level().getServer()", expected=2)
replace_exact(status_sync, "subject.getServer()", "subject.level().getServer()", expected=2)

replace_exact(
    source / "api/KarmaService.java",
    "actor.getServer()",
    "actor.level().getServer()",
)

# FLASH is a ColorParticleOption in 1.21.11; fire duration is set on Entity.
abilities = source / "gameplay/ActiveAbilityService.java"
replace_exact(
    abilities,
    "import net.minecraft.core.particles.ParticleTypes;",
    "import net.minecraft.core.particles.ColorParticleOption;\nimport net.minecraft.core.particles.ParticleTypes;",
)
replace_exact(
    abilities,
    "ParticleTypes.FLASH",
    "ColorParticleOption.create(ParticleTypes.FLASH, 0xFFFFFF)",
    expected=2,
)
replace_exact(abilities, ".setSecondsOnFire(", ".igniteForSeconds(", expected=2)

print("Applied Minecraft 1.21.11 compatibility patches successfully.")


# Heaven & Hell v0.3.1 gameplay, cosmetics, and GUI upgrade.
def replace_upgrade(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"Upgrade patch safety check failed for {path}: expected {expected} occurrence(s), found {count}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")

# Remove stale race/dimension debuffs without touching stronger or longer effects from other mods.
passives = source / "gameplay/PassiveAbilityService.java"
replace_upgrade(passives, "import net.minecraft.world.phys.AABB;\n",
    "import net.minecraft.world.phys.AABB;\n\nimport java.util.HashMap;\nimport java.util.Map;\nimport java.util.UUID;\n")
replace_upgrade(passives, "    private static long tickCounter;\n",
    "    private static long tickCounter;\n    private static final Map<UUID, Map<net.minecraft.core.Holder<net.minecraft.world.effect.MobEffect>, Long>> OWNED_DIMENSIONAL_DEBUFFS = new HashMap<>();\n")
replace_upgrade(passives,
    "        PlayerData data = HeavenHell.DATA.get(player.getUUID());\n        if (data.race == Race.HUMAN || data.isPowerless()) return;\n        Rank rank = data.rank();\n        ServerLevel level = player.level();\n",
    "        PlayerData data = HeavenHell.DATA.get(player.getUUID());\n        ServerLevel level = player.level();\n        updateDimensionalWeakness(player, data, level);\n        if (data.race == Race.HUMAN || data.isPowerless()) return;\n        Rank rank = data.rank();\n")
replace_upgrade(passives,
    "            if (passivePulse && HeavenHell.CONFIG.netherAngelWeakness && level.dimension() == net.minecraft.world.level.Level.NETHER) {\n                applyWithoutDowngrading(player, MobEffects.WEAKNESS, 0, 45);\n                applyWithoutDowngrading(player, MobEffects.SLOWNESS, 0, 45);\n            }\n", "")
replace_upgrade(passives,
    "            if (passivePulse && HeavenHell.CONFIG.overworldDemonWeakness && level.dimension() == net.minecraft.world.level.Level.OVERWORLD) {\n                applyWithoutDowngrading(player, MobEffects.WEAKNESS, 0, 45);\n                applyWithoutDowngrading(player, MobEffects.SLOWNESS, 0, 45);\n            }\n", "")
passive_helper = """    private static void updateDimensionalWeakness(ServerPlayer player, PlayerData data, ServerLevel level) {
        boolean powered = !data.isPowerless();
        boolean demonWeakness = powered && data.race == Race.DEMON && isDemonRank(data.rank())
                && HeavenHell.CONFIG.overworldDemonWeakness
                && level.dimension() == net.minecraft.world.level.Level.OVERWORLD;
        boolean angelWeakness = powered && data.race == Race.ANGEL && isAngelRank(data.rank())
                && HeavenHell.CONFIG.netherAngelWeakness
                && level.dimension() == net.minecraft.world.level.Level.NETHER;

        if (demonWeakness || angelWeakness) {
            int duration = Math.max(45, Math.max(10, HeavenHell.CONFIG.passivePulseTicks) + 5);
            applyTrackedDimensionalEffect(player, MobEffects.WEAKNESS, duration);
            applyTrackedDimensionalEffect(player, MobEffects.SLOWNESS, duration);
        } else {
            clearTrackedDimensionalEffect(player, MobEffects.WEAKNESS);
            clearTrackedDimensionalEffect(player, MobEffects.SLOWNESS);
        }
    }

    private static void applyTrackedDimensionalEffect(ServerPlayer player,
            net.minecraft.core.Holder<net.minecraft.world.effect.MobEffect> effect, int duration) {
        MobEffectInstance current = player.getEffect(effect);
        if (current == null || current.getAmplifier() < 0
                || (current.getAmplifier() == 0 && current.getDuration() < duration / 2)) {
            player.addEffect(new MobEffectInstance(effect, duration, 0, true, false, false));
            OWNED_DIMENSIONAL_DEBUFFS.computeIfAbsent(player.getUUID(), ignored -> new HashMap<>())
                    .put(effect, tickCounter + duration);
        }
    }

    private static void clearTrackedDimensionalEffect(ServerPlayer player,
            net.minecraft.core.Holder<net.minecraft.world.effect.MobEffect> effect) {
        Map<net.minecraft.core.Holder<net.minecraft.world.effect.MobEffect>, Long> owned =
                OWNED_DIMENSIONAL_DEBUFFS.get(player.getUUID());
        MobEffectInstance current = player.getEffect(effect);
        if (owned == null) {
            // Clean up short hidden effects left by pre-upgrade builds, but leave visible or long effects alone.
            if (current != null && current.getAmplifier() == 0 && current.isAmbient()
                    && !current.isVisible() && current.getDuration() <= 45) {
                player.removeEffect(effect);
            }
            return;
        }
        Long expiresAt = owned.remove(effect);
        if (expiresAt != null) {
            long expectedRemaining = Math.max(0L, expiresAt - tickCounter);
            // Do not erase a stronger or longer effect supplied by another mod/plugin.
            if (current != null && current.getAmplifier() == 0
                    && current.getDuration() <= expectedRemaining + 2L) {
                player.removeEffect(effect);
            }
        }
        if (owned.isEmpty()) OWNED_DIMENSIONAL_DEBUFFS.remove(player.getUUID());
    }

"""
replace_upgrade(passives, "    private static void applyWithoutDowngrading(ServerPlayer player,\n", passive_helper + "    private static void applyWithoutDowngrading(ServerPlayer player,\n")

# Stronger defaults, config migration, and bounded terrain-destruction controls.
config = source / "config/HeavenHellConfig.java"
replace_upgrade(config,
    "    public boolean overworldDemonWeakness = true, netherAngelWeakness = true;\n    public boolean purificationEnabled = true;\n",
    "    public boolean overworldDemonWeakness = true, netherAngelWeakness = true;\n    public boolean terrainDestructionEnabled = true;\n    public int infernalBlastTerrainRadius = 2, infernalBlastTerrainDepth = 1;\n    public int infernalCataclysmTerrainRadius = 4, infernalCataclysmTerrainDepth = 3;\n    public boolean purificationEnabled = true;\n")
replace_upgrade(config, "    public float holyBurstDamage = 4.0f, holyBurstHeal = 4.0f, holyBurstRadius = 6.0f, holyBurstKnockback = 0.9f;\n    public float divineJudgementDamage = 8.0f, divineJudgementRange = 15.0f;\n",
    "    public float holyBurstDamage = 6.0f, holyBurstHeal = 4.0f, holyBurstRadius = 6.0f, holyBurstKnockback = 0.9f;\n    public float divineJudgementDamage = 10.0f, divineJudgementRange = 15.0f;\n")
replace_upgrade(config, "    public float infernalBlastDamage = 4.0f, infernalBlastRadius = 6.0f, infernalBlastKnockback = 0.9f;\n",
    "    public float infernalBlastDamage = 7.0f, infernalBlastRadius = 6.0f, infernalBlastKnockback = 0.9f;\n")
replace_upgrade(config, "    public float hellfireChainsDamage = 6.0f, hellfireChainsRange = 12.0f, hellfireChainsPullStrength = 1.2f;\n",
    "    public float hellfireChainsDamage = 9.0f, hellfireChainsRange = 12.0f, hellfireChainsPullStrength = 1.2f;\n")
replace_upgrade(config, "    public float zoneDamage = 2.0f, zoneAllyHeal = 2.0f, cataclysmEruptionChance = 0.35f;\n",
    "    public float zoneDamage = 3.0f, zoneAllyHeal = 2.0f, cataclysmEruptionChance = 0.35f;\n")
replace_upgrade(config,
    "            if (loaded == null) loaded = new HeavenHellConfig();\n            loaded.sanitize();\n            return loaded;\n",
    "            if (loaded == null) loaded = new HeavenHellConfig();\n            boolean migrated = loaded.upgradeLegacyDefaults();\n            loaded.sanitize();\n            if (migrated) Files.writeString(path, GSON.toJson(loaded));\n            return loaded;\n")
replace_upgrade(config, "        purificationConfirmSeconds = clamp(purificationConfirmSeconds, 3, 30);\n",
    "        purificationConfirmSeconds = clamp(purificationConfirmSeconds, 3, 30);\n        infernalBlastTerrainRadius = clamp(infernalBlastTerrainRadius, 1, 4);\n        infernalBlastTerrainDepth = clamp(infernalBlastTerrainDepth, 1, 3);\n        infernalCataclysmTerrainRadius = clamp(infernalCataclysmTerrainRadius, 1, 6);\n        infernalCataclysmTerrainDepth = clamp(infernalCataclysmTerrainDepth, 1, 4);\n")
config_helper = """    /** Updates untouched v0.3 defaults while preserving deliberate server-owner tuning. */
    private boolean upgradeLegacyDefaults() {
        boolean changed = false;
        if (Float.compare(holyBurstDamage, 4.0f) == 0) { holyBurstDamage = 6.0f; changed = true; }
        if (Float.compare(divineJudgementDamage, 8.0f) == 0) { divineJudgementDamage = 10.0f; changed = true; }
        if (Float.compare(infernalBlastDamage, 4.0f) == 0) { infernalBlastDamage = 7.0f; changed = true; }
        if (Float.compare(hellfireChainsDamage, 6.0f) == 0) { hellfireChainsDamage = 9.0f; changed = true; }
        if (Float.compare(zoneDamage, 2.0f) == 0) { zoneDamage = 3.0f; changed = true; }
        return changed;
    }

"""
replace_upgrade(config, "    private static int clamp(int value, int min, int max)", config_helper + "    private static int clamp(int value, int min, int max)")

# Increase active damage and add small no-drop craters to the two infernal explosive abilities.
abilities = source / "gameplay/ActiveAbilityService.java"
replace_upgrade(abilities, "import net.minecraft.core.particles.ParticleTypes;\n",
    "import net.minecraft.core.particles.ParticleTypes;\nimport net.minecraft.core.BlockPos;\n")
replace_upgrade(abilities, "import net.minecraft.world.level.ClipContext;\n",
    "import net.minecraft.world.level.ClipContext;\nimport net.minecraft.world.level.block.Block;\n")
replace_upgrade(abilities,
    "        for (LivingEntity target : nearbyLiving(player, radius)) {\n            if (isEnemy(player, target)) {\n                target.hurt(player.damageSources().playerAttack(player), HeavenHell.CONFIG.infernalBlastDamage);\n                target.igniteForSeconds(HeavenHell.CONFIG.infernalBlastFireSeconds);\n                pushAway(player, target, HeavenHell.CONFIG.infernalBlastKnockback);\n            }\n        }\n        return true;\n",
    "        for (LivingEntity target : nearbyLiving(player, radius)) {\n            if (isEnemy(player, target)) {\n                target.hurt(player.damageSources().playerAttack(player), HeavenHell.CONFIG.infernalBlastDamage);\n                target.igniteForSeconds(HeavenHell.CONFIG.infernalBlastFireSeconds);\n                pushAway(player, target, HeavenHell.CONFIG.infernalBlastKnockback);\n            }\n        }\n        destroyTerrainCrater(player, HeavenHell.CONFIG.infernalBlastTerrainRadius,\n                HeavenHell.CONFIG.infernalBlastTerrainDepth, 36);\n        return true;\n")
replace_upgrade(abilities,
    "        level.sendParticles(ParticleTypes.SMOKE, player.getX(), player.getY() + 0.2, player.getZ(), 45, radius / 1.8, 0.3, radius / 1.8, 0.04);\n        ZONES.add(new Zone(player, Race.DEMON, radius, HeavenHell.CONFIG.infernalCataclysmDurationSeconds * 20));\n",
    "        level.sendParticles(ParticleTypes.SMOKE, player.getX(), player.getY() + 0.2, player.getZ(), 45, radius / 1.8, 0.3, radius / 1.8, 0.04);\n        destroyTerrainCrater(player, HeavenHell.CONFIG.infernalCataclysmTerrainRadius,\n                HeavenHell.CONFIG.infernalCataclysmTerrainDepth, 112);\n        ZONES.add(new Zone(player, Race.DEMON, radius, HeavenHell.CONFIG.infernalCataclysmDurationSeconds * 20));\n")
terrain_helper = """    /**
     * Carves a small, controlled crater without drops. It only removes ordinary, breakable
     * terrain; protected positions, block entities, liquids and hard/valuable blocks are kept.
     */
    private static void destroyTerrainCrater(ServerPlayer owner, int radius, int depth, int maxBlocks) {
        if (!HeavenHell.CONFIG.terrainDestructionEnabled) return;
        ServerLevel level = owner.level();
        int centerX = owner.blockPosition().getX();
        int centerY = owner.blockPosition().getY();
        int centerZ = owner.blockPosition().getZ();
        int destroyed = 0;
        int safeRadius = Math.max(1, Math.min(radius, 6));
        int safeDepth = Math.max(1, Math.min(depth, 4));

        for (int dx = -safeRadius; dx <= safeRadius; dx++) {
            for (int dz = -safeRadius; dz <= safeRadius; dz++) {
                double distance = Math.sqrt(dx * dx + dz * dz);
                if (distance > safeRadius) continue;
                int columnDepth = Math.max(1, safeDepth - (int) Math.floor(distance / safeRadius * safeDepth));
                for (int dy = 0; dy < columnDepth; dy++) {
                    BlockPos pos = new BlockPos(centerX + dx, centerY - 1 - dy, centerZ + dz);
                    var state = level.getBlockState(pos);
                    float hardness = state.getDestroySpeed(level, pos);
                    if (state.isAir() || state.hasBlockEntity() || !state.getFluidState().isEmpty()
                            || hardness < 0.0f || hardness > 2.5f || !level.mayInteract(owner, pos)) continue;
                    level.levelEvent(2001, pos, Block.getId(state));
                    if (level.destroyBlock(pos, false, owner) && ++destroyed >= maxBlocks) return;
                }
            }
        }
    }

"""
replace_upgrade(abilities, "    private static LivingEntity findLookTarget(ServerPlayer player, double range) {", terrain_helper + "    private static LivingEntity findLookTarget(ServerPlayer player, double range) {")

# The cosmetic model is rendered in two passes: wings from the torso pivot and headwear from the head pivot.
model_path = source / "client/render/RaceWingsModel.java"
if not model_path.exists() or "class RaceWingsModel" not in model_path.read_text(encoding="utf-8"):
    raise SystemExit(f"Expected race wing model not found: {model_path}")
model_path.write_text("""package com.kuku.heavenhell.client.render;

import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.client.renderer.entity.state.AvatarRenderState;

/** Large, animated cosmetic wings plus head-anchored halo and horns. */
public final class RaceWingsModel extends EntityModel<AvatarRenderState> {
    private final ModelPart leftWing;
    private final ModelPart rightWing;
    private final ModelPart leftWingTwo;
    private final ModelPart rightWingTwo;
    private final ModelPart leftWingThree;
    private final ModelPart rightWingThree;
    private final ModelPart halo;
    private final ModelPart leftHorn;
    private final ModelPart rightHorn;

    public RaceWingsModel(ModelPart root) {
        super(root);
        leftWing = root.getChild("left_wing");
        rightWing = root.getChild("right_wing");
        leftWingTwo = root.getChild("left_wing_two");
        rightWingTwo = root.getChild("right_wing_two");
        leftWingThree = root.getChild("left_wing_three");
        rightWingThree = root.getChild("right_wing_three");
        halo = root.getChild("halo");
        leftHorn = root.getChild("left_horn");
        rightHorn = root.getChild("right_horn");
    }

    public static LayerDefinition createLayer() {
        MeshDefinition mesh = new MeshDefinition();
        PartDefinition root = mesh.getRoot();
        CubeDeformation thin = new CubeDeformation(0.035F);

        addWing(root, "left_wing", 1, -9.2F, 2.55F, 1.0F, 0.0F, thin);
        addWing(root, "right_wing", -1, -9.2F, 2.55F, 1.0F, 0.0F, thin);
        addWing(root, "left_wing_two", 1, -8.3F, 2.72F, 0.88F, 0.20F, thin);
        addWing(root, "right_wing_two", -1, -8.3F, 2.72F, 0.88F, -0.20F, thin);
        addWing(root, "left_wing_three", 1, -9.8F, 2.88F, 1.08F, -0.18F, thin);
        addWing(root, "right_wing_three", -1, -9.8F, 2.88F, 1.08F, 0.18F, thin);

        root.addOrReplaceChild("halo", CubeListBuilder.create()
                .texOffs(0, 48).addBox(-4.0F, 0.0F, -1.0F, 8.0F, 0.65F, 1.0F, thin)
                .texOffs(0, 48).addBox(-4.0F, 0.0F, 2.0F, 8.0F, 0.65F, 1.0F, thin)
                .texOffs(0, 52).addBox(-4.0F, 0.0F, -1.0F, 1.0F, 0.65F, 3.0F, thin)
                .texOffs(0, 52).addBox(3.0F, 0.0F, -1.0F, 1.0F, 0.65F, 3.0F, thin),
                PartPose.offset(0.0F, -9.35F, 0.0F));
        root.addOrReplaceChild("left_horn", CubeListBuilder.create().texOffs(32, 48)
                .addBox(-0.8F, -4.2F, -0.4F, 1.6F, 5.2F, 1.6F, thin),
                PartPose.offsetAndRotation(3.2F, -6.4F, 0.1F, 0.0F, 0.0F, 0.32F));
        root.addOrReplaceChild("right_horn", CubeListBuilder.create().texOffs(32, 48)
                .addBox(-0.8F, -4.2F, -0.4F, 1.6F, 5.2F, 1.6F, thin),
                PartPose.offsetAndRotation(-3.2F, -6.4F, 0.1F, 0.0F, 0.0F, -0.32F));
        return LayerDefinition.create(mesh, 64, 64);
    }

    private static void addWing(PartDefinition root, String name, int side, float y, float z,
                                float scale, float baseRotation, CubeDeformation deformation) {
        CubeListBuilder cubes = CubeListBuilder.create()
                .texOffs(0, 0).addBox(x(side, 0.0F, 2.0F, scale), -2.0F * scale, 0.0F, 2.0F * scale, 5.0F * scale, 1.0F, deformation)
                .texOffs(10, 0).addBox(x(side, 1.0F, 2.0F, scale), -1.0F * scale, 0.0F, 2.0F * scale, 10.0F * scale, 1.0F, deformation)
                .texOffs(22, 0).addBox(x(side, 2.5F, 2.0F, scale), 1.0F * scale, 0.0F, 2.0F * scale, 14.0F * scale, 1.0F, deformation)
                .texOffs(34, 0).addBox(x(side, 4.0F, 2.0F, scale), 3.0F * scale, 0.0F, 2.0F * scale, 13.0F * scale, 1.0F, deformation)
                .texOffs(46, 0).addBox(x(side, 5.2F, 1.0F, scale), 5.0F * scale, 0.0F, 1.0F * scale, 9.0F * scale, 1.0F, deformation);
        root.addOrReplaceChild(name, cubes,
                PartPose.offsetAndRotation(side * 2.0F, y, z, 0.0F, side * 0.05F, side * baseRotation));
    }

    private static float x(int side, float start, float width, float scale) {
        float scaledStart = start * scale;
        float scaledWidth = width * scale;
        return side > 0 ? scaledStart : -scaledStart - scaledWidth;
    }

    public void configureWings(int raceId, int rankId) {
        boolean angel = raceId == 1;
        leftWing.visible = rightWing.visible = rankId > 0;
        leftWingTwo.visible = rightWingTwo.visible = angel ? rankId >= 2 : rankId >= 5;
        leftWingThree.visible = rightWingThree.visible = angel ? rankId >= 3 : rankId >= 6;
        halo.visible = false;
        leftHorn.visible = rightHorn.visible = false;
    }

    public void configureHead(int raceId, int rankId) {
        boolean angel = raceId == 1;
        leftWing.visible = rightWing.visible = false;
        leftWingTwo.visible = rightWingTwo.visible = false;
        leftWingThree.visible = rightWingThree.visible = false;
        halo.visible = angel && rankId > 0;
        leftHorn.visible = rightHorn.visible = !angel && rankId > 0;
    }

    @Override
    public void setupAnim(AvatarRenderState state) {
        root().resetPose();
        float phase = state.ageInTicks * 0.16F;
        float flap = (float) Math.sin(phase) * 0.22F;
        float secondary = (float) Math.sin(phase - 0.35F) * 0.18F;
        float tertiary = (float) Math.sin(phase + 0.25F) * 0.16F;
        leftWing.zRot = 0.20F + flap;
        rightWing.zRot = -0.20F - flap;
        leftWingTwo.zRot = 0.34F + secondary;
        rightWingTwo.zRot = -0.34F - secondary;
        leftWingThree.zRot = 0.46F + tertiary;
        rightWingThree.zRot = -0.46F - tertiary;
        leftWing.xRot = rightWing.xRot = (float) Math.sin(phase) * 0.08F;
        leftWingTwo.xRot = rightWingTwo.xRot = (float) Math.sin(phase - 0.35F) * 0.07F;
        leftWingThree.xRot = rightWingThree.xRot = (float) Math.sin(phase + 0.25F) * 0.07F;
        halo.yRot = state.ageInTicks * 0.025F;
    }
}
""", encoding="utf-8")

layer_path = source / "client/render/RaceWingsLayer.java"
if not layer_path.exists() or "class RaceWingsLayer" not in layer_path.read_text(encoding="utf-8"):
    raise SystemExit(f"Expected race wing layer not found: {layer_path}")
layer_path.write_text("""package com.kuku.heavenhell.client.render;

import com.kuku.heavenhell.HeavenHell;
import com.kuku.heavenhell.client.PlayerStatusCache;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.player.PlayerModel;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.entity.state.AvatarRenderState;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.Identifier;

/** Client-only cosmetics, anchored to vanilla torso/head parts and driven by server status. */
public final class RaceWingsLayer extends RenderLayer<AvatarRenderState, PlayerModel> {
    private static final Identifier ANGEL_TEXTURE = Identifier.fromNamespaceAndPath(
            HeavenHell.MOD_ID, "textures/entity/angel_wings.png");
    private static final Identifier DEMON_TEXTURE = Identifier.fromNamespaceAndPath(
            HeavenHell.MOD_ID, "textures/entity/demon_wings.png");

    private final RaceWingsModel model;

    public RaceWingsLayer(RenderLayerParent<AvatarRenderState, PlayerModel> parent, ModelPart bakedRoot) {
        super(parent);
        this.model = new RaceWingsModel(bakedRoot);
    }

    @Override
    public void submit(PoseStack matrices, SubmitNodeCollector queue, int packedLight,
                       AvatarRenderState state, float limbAngle, float limbDistance) {
        PlayerStatusCache.Status status = PlayerStatusCache.get(state.id);
        if (status == null || !status.isPowered() || state.isInvisible || state.isSpectator) return;
        Identifier texture = status.isAngel() ? ANGEL_TEXTURE : DEMON_TEXTURE;
        int tint = 0xFFFFFFFF;

        matrices.pushPose();
        getParentModel().body.translateAndRotate(matrices);
        matrices.translate(0.0, 0.0, 0.10);
        model.configureWings(status.raceId(), status.rankId());
        model.setupAnim(state);
        renderColoredCutoutModel(model, texture, matrices, queue, packedLight, state, tint, OverlayTexture.NO_OVERLAY);
        matrices.popPose();

        matrices.pushPose();
        getParentModel().head.translateAndRotate(matrices);
        model.configureHead(status.raceId(), status.rankId());
        model.setupAnim(state);
        renderColoredCutoutModel(model, texture, matrices, queue, packedLight, state, tint, OverlayTexture.NO_OVERLAY);
        matrices.popPose();
    }
}
""", encoding="utf-8")

# Avoid the duplicate blur submission that crashed the V-key status screen.
screen = source / "client/RaceStatusScreen.java"
replace_upgrade(screen, "        renderBackground(graphics, mouseX, mouseY, delta);\n",
    "        graphics.fill(0, 0, this.width, this.height, 0xB0000000);\n")

# Keep the shipped example configuration aligned with the new defaults and toggles.
example = project / "config/heavenhell.example.json"
replace_upgrade(example, '  "netherAngelWeakness": true,\n',
    '  "netherAngelWeakness": true,\n  "terrainDestructionEnabled": true,\n  "infernalBlastTerrainRadius": 2,\n  "infernalBlastTerrainDepth": 1,\n  "infernalCataclysmTerrainRadius": 4,\n  "infernalCataclysmTerrainDepth": 3,\n')
replace_upgrade(example, '  "holyBurstDamage": 4.0,', '  "holyBurstDamage": 6.0,')
replace_upgrade(example, '  "divineJudgementDamage": 8.0,', '  "divineJudgementDamage": 10.0,')
replace_upgrade(example, '  "infernalBlastDamage": 4.0,', '  "infernalBlastDamage": 7.0,')
replace_upgrade(example, '  "hellfireChainsDamage": 6.0,', '  "hellfireChainsDamage": 9.0,')
replace_upgrade(example, '  "zoneDamage": 2.0,', '  "zoneDamage": 3.0,')

print("Applied Heaven & Hell v0.3.1 gameplay, cosmetic, and GUI upgrades.")
