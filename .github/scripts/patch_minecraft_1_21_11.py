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



# Heaven & Hell v0.4 gameplay and presentation updates.
import base64

passives = source / "gameplay/PassiveAbilityService.java"
replace_exact(passives, "import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;\n",
    "import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;\nimport net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;\n")
replace_exact(passives, "import net.minecraft.server.level.ServerPlayer;\n",
    "import net.minecraft.server.level.ServerPlayer;\nimport net.minecraft.tags.DamageTypeTags;\n")
replace_exact(passives,
    """    public static void register() {
        ServerTickEvents.END_SERVER_TICK.register(PassiveAbilityService::onServerTick);
    }
""",
    """    public static void register() {
        ServerTickEvents.END_SERVER_TICK.register(PassiveAbilityService::onServerTick);
        ServerLivingEntityEvents.ALLOW_DAMAGE.register((entity, damageSource, amount) -> {
            if (!(entity instanceof ServerPlayer player) || !damageSource.is(DamageTypeTags.IS_FALL)) return true;
            PlayerData data = HeavenHell.DATA.get(player.getUUID());
            return data.race != Race.ANGEL || data.isPowerless()
                    || (data.rank() != Rank.ARCHANGEL && data.rank() != Rank.SERAPHIM);
        });
    }
""")
replace_exact(passives,
    """                if (!player.onGround() && player.getDeltaMovement().y < -0.15) {
                    applyWithoutDowngrading(player, MobEffects.SLOW_FALLING, 0, 25);
                }
""", "")
replace_exact(passives,
    """        for (ServerPlayer target : level.players()) {
            if (target == player || player.distanceToSqr(target) > radiusSquared) continue;
            if (!HeavenHell.CONFIG.friendlyFire && player.isAlliedTo(target)) continue;
            applyWithoutDowngrading(target, MobEffects.WEAKNESS, 0, pulse + 10);
        }
""",
    """        for (ServerPlayer target : level.players()) {
            if (target == player || player.distanceToSqr(target) > radiusSquared) continue;
            PlayerData targetData = HeavenHell.DATA.get(target.getUUID());
            if (targetData.race == Race.DEMON || player.isAlliedTo(target)) continue;
            applyWithoutDowngrading(target, MobEffects.WEAKNESS, 0, pulse + 10);
        }
""")

abilities = source / "gameplay/ActiveAbilityService.java"
replace_exact(abilities, "import net.minecraft.core.BlockPos;\n",
    "import net.minecraft.core.BlockPos;\nimport net.minecraft.world.entity.EntitySpawnReason;\nimport net.minecraft.world.entity.EntityType;\nimport net.minecraft.world.entity.LightningBolt;\n")
replace_exact(abilities, "    private static final List<Zone> ZONES = new ArrayList<>();\n",
    "    private static final List<Zone> ZONES = new ArrayList<>();\n    private static final List<PendingMeteor> METEORS = new ArrayList<>();\n")
replace_exact(abilities, "        ZONES.removeIf(zone -> zone.owner.equals(playerId));\n",
    "        ZONES.removeIf(zone -> zone.owner.equals(playerId));\n        METEORS.removeIf(meteor -> meteor.owner.equals(playerId));\n", expected=2)
replace_exact(abilities,
    """        ZONES.add(new Zone(player, Race.DEMON, radius, HeavenHell.CONFIG.infernalCataclysmDurationSeconds * 20));
        return true;
""",
    """        ZONES.add(new Zone(player, Race.DEMON, radius, HeavenHell.CONFIG.infernalCataclysmDurationSeconds * 20));
        summonMiniMeteors(player, 8, radius * 0.88);
        return true;
""")
replace_exact(abilities,
    """        if (target instanceof ServerPlayer other) {
            return other != owner && (HeavenHell.CONFIG.friendlyFire || !owner.isAlliedTo(other));
        }
""",
    """        if (target instanceof ServerPlayer other) {
            if (other == owner) return false;
            PlayerData ownerData = HeavenHell.DATA.get(owner.getUUID());
            PlayerData targetData = HeavenHell.DATA.get(other.getUUID());
            if (ownerData.race != Race.HUMAN && ownerData.race == targetData.race) return false;
            if (ownerData.race == Race.DEMON && owner.isAlliedTo(other)) return false;
            return HeavenHell.CONFIG.friendlyFire || !owner.isAlliedTo(other);
        }
""")
replace_exact(abilities,
    """                entity.hurt(owner.damageSources().playerAttack(owner), HeavenHell.CONFIG.zoneDamage);
            } else {
""",
    """                strikeHolyLightning(zone, owner, entity);
            } else {
""")
replace_exact(abilities, "        Iterator<Zone> zoneIterator = ZONES.iterator();\n",
    """        Iterator<PendingMeteor> meteorIterator = METEORS.iterator();
        while (meteorIterator.hasNext()) {
            PendingMeteor meteor = meteorIterator.next();
            ServerPlayer owner = server.getPlayerList().getPlayer(meteor.owner);
            PlayerData ownerData = owner == null ? null : HeavenHell.DATA.get(owner.getUUID());
            if (owner == null || !owner.isAlive() || owner.level() != meteor.level
                    || ownerData == null || ownerData.race != Race.DEMON || ownerData.isPowerless()
                    || ownerData.rank() != Rank.DEMON_LORD) {
                meteorIterator.remove();
                continue;
            }
            meteor.ticksLeft--;
            double trailY = meteor.impact.y + Math.max(0.0, meteor.ticksLeft) * 0.68 + 0.8;
            meteor.level.sendParticles(ParticleTypes.FLAME, meteor.impact.x, trailY, meteor.impact.z,
                    10, 0.28, 0.35, 0.28, 0.055);
            meteor.level.sendParticles(ParticleTypes.SMOKE, meteor.impact.x, trailY + 0.25, meteor.impact.z,
                    5, 0.20, 0.25, 0.20, 0.025);
            if (meteor.ticksLeft <= 0) {
                impactMeteor(owner, meteor);
                meteorIterator.remove();
            }
        }

        Iterator<Zone> zoneIterator = ZONES.iterator();
""")
replace_exact(abilities,
    """    /**
     * Carves a small, controlled crater without drops. It only removes ordinary, breakable
""",
    """    private static void strikeHolyLightning(Zone zone, ServerPlayer owner, LivingEntity target) {
        LightningBolt bolt = EntityType.LIGHTNING_BOLT.create(zone.level, EntitySpawnReason.TRIGGERED);
        if (bolt != null) {
            bolt.setVisualOnly(true);
            bolt.setPos(target.getX(), target.getY(), target.getZ());
            zone.level.addFreshEntity(bolt);
        }
        target.hurt(zone.level.damageSources().magic(), HeavenHell.CONFIG.zoneDamage);
        zone.level.sendParticles(ParticleTypes.ELECTRIC_SPARK, target.getX(), target.getY() + 0.9,
                target.getZ(), 26, 0.42, 0.8, 0.42, 0.12);
    }

    private static void summonMiniMeteors(ServerPlayer owner, int count, double radius) {
        ServerLevel level = owner.level();
        for (int i = 0; i < count; i++) {
            double angle = owner.getRandom().nextDouble() * Math.PI * 2.0;
            double distance = Math.sqrt(owner.getRandom().nextDouble()) * radius;
            int x = (int) Math.floor(owner.getX() + Math.cos(angle) * distance);
            int z = (int) Math.floor(owner.getZ() + Math.sin(angle) * distance);
            BlockPos surface = level.getHeightmapPos(net.minecraft.world.level.levelgen.Heightmap.Types.MOTION_BLOCKING,
                    new BlockPos(x, owner.blockPosition().getY(), z));
            Vec3 impact = new Vec3(x + 0.5, surface.getY() + 0.15, z + 0.5);
            METEORS.add(new PendingMeteor(owner.getUUID(), level, impact, 12 + owner.getRandom().nextInt(34)));
        }
    }

    private static void impactMeteor(ServerPlayer owner, PendingMeteor meteor) {
        Vec3 point = meteor.impact;
        double radius = 2.65;
        meteor.level.sendParticles(ParticleTypes.EXPLOSION_EMITTER, point.x, point.y + 0.1, point.z, 1, 0, 0, 0, 0);
        meteor.level.sendParticles(ParticleTypes.FLAME, point.x, point.y + 0.2, point.z, 48, 0.8, 0.35, 0.8, 0.12);
        meteor.level.sendParticles(ParticleTypes.LAVA, point.x, point.y + 0.1, point.z, 12, 0.65, 0.15, 0.65, 0.02);
        meteor.level.sendParticles(ParticleTypes.SMOKE, point.x, point.y + 0.4, point.z, 24, 0.6, 0.35, 0.6, 0.06);
        AABB area = new AABB(point.x - radius, point.y - 1.5, point.z - radius,
                point.x + radius, point.y + 2.5, point.z + radius);
        for (LivingEntity target : meteor.level.getEntitiesOfClass(LivingEntity.class, area,
                e -> e.isAlive() && !(e instanceof ArmorStand)
                        && e.position().distanceToSqr(point) <= radius * radius && isEnemy(owner, e))) {
            target.hurt(owner.damageSources().playerAttack(owner), 10.0f);
            target.igniteForSeconds(4);
            Vec3 away = target.position().subtract(point);
            if (away.lengthSqr() < 0.0001) away = new Vec3(0, 0, 1);
            away = away.normalize();
            target.setDeltaMovement(target.getDeltaMovement().add(away.x * 0.75, 0.35, away.z * 0.75));
            target.hurtMarked = true;
        }
    }

    /**
     * Carves a small, controlled crater without drops. It only removes ordinary, breakable
""")
replace_exact(abilities, "    private static final class Zone {\n",
    """    private static final class PendingMeteor {
        final UUID owner;
        final ServerLevel level;
        final Vec3 impact;
        int ticksLeft;
        PendingMeteor(UUID owner, ServerLevel level, Vec3 impact, int ticksLeft) {
            this.owner = owner; this.level = level; this.impact = impact; this.ticksLeft = ticksLeft;
        }
    }

    private static final class Zone {
""")

config = source / "config/HeavenHellConfig.java"
replace_exact(config, "public float holyBurstDamage = 6.0f,", "public float holyBurstDamage = 9.0f,")
replace_exact(config, "public float divineJudgementDamage = 10.0f,", "public float divineJudgementDamage = 16.0f,")
replace_exact(config, "public float infernalBlastDamage = 7.0f,", "public float infernalBlastDamage = 10.0f,")
replace_exact(config, "public float hellfireChainsDamage = 9.0f,", "public float hellfireChainsDamage = 14.0f,")
replace_exact(config, "public float zoneDamage = 3.0f,", "public float zoneDamage = 5.0f,")
replace_exact(config,
    """        if (Float.compare(zoneDamage, 2.0f) == 0) { zoneDamage = 3.0f; changed = true; }
        return changed;
""",
    """        if (Float.compare(zoneDamage, 2.0f) == 0) { zoneDamage = 3.0f; changed = true; }
        if (Float.compare(holyBurstDamage, 6.0f) == 0) { holyBurstDamage = 9.0f; changed = true; }
        if (Float.compare(divineJudgementDamage, 10.0f) == 0) { divineJudgementDamage = 16.0f; changed = true; }
        if (Float.compare(infernalBlastDamage, 7.0f) == 0) { infernalBlastDamage = 10.0f; changed = true; }
        if (Float.compare(hellfireChainsDamage, 9.0f) == 0) { hellfireChainsDamage = 14.0f; changed = true; }
        if (Float.compare(zoneDamage, 3.0f) == 0) { zoneDamage = 5.0f; changed = true; }
        return changed;
""")

layer = source / "client/render/RaceWingsLayer.java"
replace_exact(layer, "        matrices.translate(0.0, 0.0, 0.10);\n",
    "        matrices.translate(0.0, 0.0, 0.19);\n        matrices.scale(1.42F, 1.42F, 1.0F);\n")
model = source / "client/render/RaceWingsModel.java"
replace_exact(model,
    """        addWing(root, "left_wing", 1, -9.2F, 2.55F, 1.0F, 0.0F, thin);
        addWing(root, "right_wing", -1, -9.2F, 2.55F, 1.0F, 0.0F, thin);
        addWing(root, "left_wing_two", 1, -8.3F, 2.72F, 0.88F, 0.20F, thin);
        addWing(root, "right_wing_two", -1, -8.3F, 2.72F, 0.88F, -0.20F, thin);
        addWing(root, "left_wing_three", 1, -9.8F, 2.88F, 1.08F, -0.18F, thin);
        addWing(root, "right_wing_three", -1, -9.8F, 2.88F, 1.08F, 0.18F, thin);
""",
    """        addWing(root, "left_wing", 1, -8.8F, 2.75F, 1.22F, 0.0F, thin);
        addWing(root, "right_wing", -1, -8.8F, 2.75F, 1.22F, 0.0F, thin);
        addWing(root, "left_wing_two", 1, -8.0F, 2.92F, 1.08F, 0.20F, thin);
        addWing(root, "right_wing_two", -1, -8.0F, 2.92F, 1.08F, -0.20F, thin);
        addWing(root, "left_wing_three", 1, -9.4F, 3.08F, 1.28F, -0.18F, thin);
        addWing(root, "right_wing_three", -1, -9.4F, 3.08F, 1.28F, 0.18F, thin);
""")
textures = project / "src/main/resources/assets/heavenhell/textures/entity"
(textures / "angel_wings.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAADMUlEQVR4nO2b60/bMBTFT+g2acCgtOUN+5P3J07qi/SVPoAyjdKcfbgJdmo7fNgkD+wjWVF6kvT6yrn5tXaS7TMJAHufAb4AwzkAAEki2+sOig9kM9rxz09Q0ey+6re/Vf3lU9U//lr1F2tAIpLt7vnTVdXf/f40q/rXbQAE0JD+DXb8PQSumADfAfhW8AlANyW7KUmSvRHJl6JtpQ2n0kjybkZD44U0kpwsTT97kEaS80fTXz6Ri7Xbn92T05X7+qM5mWY78eVF25KDCdkfq/7lG3L7LO3lNxn8CHhNQH8M3J67D0wz4LLt9qcr4PTY7S/WwMmB218+1fuz+/rrj+b18Q0m9v7FEeA7AN9KShJMEiD5JEOl3Ac+EAkCQENu9UiCmmICfAfgW8EnIOmmqgjengPYlo5s7rSiZ3vOTpbKtz2n54/Ktz3nV79UUWrum372oPzOkemPF8q/aBUfUm2HWlG8OZOfxLEIaooJ8B2Ab1US0B8DaLgPTrP6i01X9f5i/Xf+W9d/K77+WGBPV4UEAUWDLhIEhAZdJAgIDbpIEBAadJEgoAqnjQQBVXhtJAgAdzPl6yRISv96I7UfbwHfAfhWTIDvAHyrQoKARoMWEgRMGtRJEDBpUCdBwKRBnQRJ09dJkDSvr5MgWcTnIEFS+pdv1H7wIyAmwHcAvhV8AiIJmqeHpYQ/f/Dtwz6u4gjYrQHDufx1NJzKvm1e4KIlAALY5wU6RwIwgH1eoLkvAATY5wVODqQOuOYFTo+lDrjmBS7bUgdsNWCQCQz1RkVNMEiwA/lPIJf9d0mCKDptIcGbthTCfBOLIACYgJiA4BMQ/FMg+BEQE+A7AN8KPgF2EgReafBdkiAhRTu3kyApi8O3z3EExATEBPgOwLesJAgoGnStEyxp0LVOsKRB1zrBkgZd6wRbh/bzy3WCZ03795frBK86RfwWEiSB7xdAN40jICYgJsB3AL4VSRCBy52AvNb9/0XUxp9vgMaX993Ff6LgE+AkwSQBrk+hlptY3hhxzQyXvmtmuPRtM8P6GyOtQ9PX3xg5a5q+/sbIVQdyK1tIEBAaDH4ExAT4DsC3/gAYmSEQf7yX5wAAAABJRU5ErkJggg=="))
(textures / "demon_wings.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAElklEQVR4nO2bzXNTVRjGf5dckKZJaSOuWbgmXWppLTilbdqmIrYgUFy4cwkWUCof1lHUoeq/4EJxoSyU2GlpGUoBOy5T/gw+gjRt/QrHxb3n3pOTk+k4whw159llnrc3p+8kv/vcc954xzI7xBc9Ccbn/8RD0J6q4AmBB3gIjnQkmbj6a/BahD4CT8BIV5rJmdWq+vbmwM93tzF94wF3yomoXl6/d892rl2/i4egWPYRgPA8BHAi38bMjfsIgtfF1dDH473BNN/f/KWqvlj2ER580J/kzOw6O9OPo3rhBf6nvVs4Of8HAtiZeozwiK6/iQaXa4DtBdhWwzfAz6YqQIJsCLflcqIaghB6AQSXFaiNSE+pX14J/DywXE5UQVNevzf0PATZVKUKaoSehFQ2XYmgFntxfTZVQQQW2VQlhmoIweD/I3ofCU0HwVCuAW++sIUvf/7NaH7S+wzf/LRm9CZzSd6fWTV6E4MtfDz9yOiN59v4/MoDo9e3ZzsXCw+N3nB3Kz/cNHujnWm+vV02emMdTXy1tG70wH0C8CEEkpLUJNQiL0SQmgQhAIsOzXYFOjo0PQR9KFDVkmAvMdSiJBj6Eqo6NItlnxFiOKrQlHBcLidqoOkgGMo1wPYCbKvhG+CDBBY1SXBMegoEJdRGUZKelgSHIbqOngSRXlivQk16KqQk1OQ69cdnY9IjhqBMsvrjs4NgKNcA2wuwrYZvgEuCT73F/3K5BthegG1tOn6tYjTGOpq4tGTeCxjtTHP51orRG+5upbBYMnon8m3MLdwzeuP5NqYK5r+bGGzho2nz+03mkpybNa/zSEeSd+Z+N3pSfjZVu2fniTixtRuS4AFiOOpJEJSkpyXByFPqJdRASXpaEpSePOhQIfia9DRoCjwOgxGaDoKKXANsL8C2Gr4Bvp7UJNQgTHortUlQeqaDlFdQkp6WBPuJE6KeBPeiJD0tCQ4RPyY/qYMUB8FQnnjrebFx2f9X7hNwLLNDmBhwNEyCdwwMONCZ4vKtFTxEMAGifKfPDKQpLJaienVC5GS+lbmFe0YGvD2cYapQqpngKK76nA6ToPDCCQ+UINTVwrnZtahenRA5vCtIgmq9fn2XBJ/Gx+q/JNcA2wuwrYZvgPEu8MaLW/l6aT2gvHYX+LC/ie9ur0T16l3g7ECKK4sPq+rlXeDUUCtThVINNItln+PDGT4rlIyUHtyd4cL0o2iPT70L7O9q4fzMWlW9vAsc2tXMpaW1Gmi6OUFNrgG2F2BbDd8AYxIELekpUIu8J3SQstEc3yBK0tOS4H7qH6Qcov5BioOgItcA2wuwrYZvgHFPEDbHe35aEjxI/ZGafcR7hfqeYA7zSE2x7NODcrqrQQ2UPT9tTzDy/uZIjYOgItcA2wuwrYZvgEuCekcu7t3MqTpn6gc7U5ydNc/e73tpW915/tzuZ5lduG/0el5+jvnrd43eu0Pb+LHOrMH5XHPd3ytc6NvK6avm30DoavivgGuA7QXYVk0ShOo5PjUJvo6S9LQk+Cr1D1IG2PggxZTUIo/qn8H9k4MUlwQ1uQbYXoBt/QUEaxwsTgsOzAAAAABJRU5ErkJggg=="))

screen = source / "client/RaceStatusScreen.java"
replace_exact(screen, "        int panelWidth = 300;\n        int panelHeight = 224;\n",
    "        int panelWidth = 340;\n        int panelHeight = 312;\n")
replace_exact(screen,
    """            String[] abilities = unlockedAbilities(status.raceId(), status.rankId());
            int lineY = dividerY + 25;
""",
    """            String[] abilities = unlockedAbilities(status.raceId(), status.rankId());
            String[] descriptions = abilityDescriptions(status.raceId(), status.rankId());
            int lineY = dividerY + 25;
""")
replace_exact(screen,
    """                    graphics.drawString(this.font, "• " + abilities[i], left + 24, lineY, 0xFFFFFFFF);
                    graphics.drawString(this.font, cooldown, left + panelWidth - 91, lineY, 0xFFBFB4D5);
                    lineY += 13;
""",
    """                    graphics.drawString(this.font, "• " + abilities[i], left + 24, lineY, 0xFFFFFFFF);
                    graphics.drawString(this.font, cooldown, left + panelWidth - 91, lineY, 0xFFBFB4D5);
                    graphics.drawString(this.font, descriptions[i], left + 34, lineY + 10, 0xFFB8AEC9);
                    lineY += 26;
""")
marker = """    @Override
    public boolean isPauseScreen() { return false; }
"""
descriptions = """    private static String[] abilityDescriptions(int race, int rank) {
        if (race == 1) {
            return switch (rank) {
                case 1 -> new String[]{"Slowly restores your health.", "Blast enemies and heal nearby allies."};
                case 2 -> new String[]{"Slowly restores your health.", "Resist damage and negate all fall damage.",
                        "Blast enemies and heal nearby allies.", "Mark and strike a distant enemy."};
                case 3 -> new String[]{"Slowly restores your health.", "Resist damage and negate all fall damage.",
                        "Immune to poison; frighten nearby hostiles.", "Blast enemies and heal nearby allies.",
                        "Mark and strike a distant enemy.", "Call armour-piercing lightning strikes."};
                default -> new String[0];
            };
        }
        if (race == 2) {
            return switch (rank) {
                case 4 -> new String[]{"Fire resistance and a chance to ignite foes.", "Explosive fire burst that ignites enemies."};
                case 5 -> new String[]{"Fire resistance and a chance to ignite foes.", "Melee hits restore health.",
                        "Explosive fire burst that ignites enemies.", "Pull and stun a targeted enemy."};
                case 6 -> new String[]{"Fire resistance and a chance to ignite foes.", "Melee hits restore health.",
                        "Weaken nearby hostile mobs and enemy players.", "Explosive fire burst that ignites enemies.",
                        "Pull and stun a targeted enemy.", "Burning zone with random mini meteors."};
                default -> new String[0];
            };
        }
        return new String[0];
    }

"""
replace_exact(screen, marker, descriptions + marker)
for old, new in [
    ('"holyBurstDamage": 6.0', '"holyBurstDamage": 9.0'),
    ('"divineJudgementDamage": 10.0', '"divineJudgementDamage": 16.0'),
    ('"infernalBlastDamage": 7.0', '"infernalBlastDamage": 10.0'),
    ('"hellfireChainsDamage": 9.0', '"hellfireChainsDamage": 14.0'),
    ('"zoneDamage": 3.0', '"zoneDamage": 5.0')
]:
    replace_exact(project / "config/heavenhell.example.json", old, new)

print("Applied Heaven & Hell v0.4 gameplay, wings, and GUI updates.")
