#!/usr/bin/env python3
"""Compatibility and command-structure fixes for Sovereigns on Minecraft 1.21.11."""
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

commands_rel = "src/main/java/com/kuku/heavenhell/command/HeavenHellCommands.java"
path = root / commands_rel
source = path.read_text(encoding="utf-8")
start_marker = '                .then(Commands.literal("boss").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))'
end_marker = '                .then(Commands.literal("reload")'
start = source.find(start_marker)
if start >= 0:
    end = source.find(end_marker, start)
    if end < 0:
        raise SystemExit("Could not find /heavenhell reload branch after Sovereigns admin commands")
    source = source[:start] + source[end:]
callback_end = '        });\n    }\n    private static void showKarma'
if 'Commands.literal("heavenhellboss")' not in source:
    standalone = r'''            dispatcher.register(Commands.literal("heavenhellboss")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .then(Commands.literal("spawn")
                    .then(Commands.argument("boss", com.mojang.brigadier.arguments.StringArgumentType.word())
                        .suggests((c, b) -> net.minecraft.commands.SharedSuggestionProvider.suggest(new String[]{"seraphiel", "malachar"}, b))
                        .executes(ctx -> {
                            String id = com.mojang.brigadier.arguments.StringArgumentType.getString(ctx, "boss");
                            if (!com.kuku.heavenhell.gameplay.SovereignBossService.spawnBoss(ctx.getSource().getLevel(), ctx.getSource().getPosition(), id)) {
                                ctx.getSource().sendFailure(Component.literal("Unknown boss or that sovereign is already active in this world."));
                                return 0;
                            }
                            ctx.getSource().sendSuccess(() -> Component.literal("Summoned " + id + ". The Sovereign encounter has begun."), true);
                            return 1;
                        })))
                .then(Commands.literal("despawn")
                    .then(Commands.argument("boss", com.mojang.brigadier.arguments.StringArgumentType.word())
                        .suggests((c, b) -> net.minecraft.commands.SharedSuggestionProvider.suggest(new String[]{"seraphiel", "malachar"}, b))
                        .executes(ctx -> {
                            String id = com.mojang.brigadier.arguments.StringArgumentType.getString(ctx, "boss");
                            if (!com.kuku.heavenhell.gameplay.SovereignBossService.despawnBoss(ctx.getSource().getServer(), id)) {
                                ctx.getSource().sendFailure(Component.literal("No active sovereign matched that name."));
                                return 0;
                            }
                            ctx.getSource().sendSuccess(() -> Component.literal("Despawned " + id + "."), true);
                            return 1;
                        }))));
            dispatcher.register(Commands.literal("heavenhellweapon")
                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                .then(Commands.literal("give")
                    .then(Commands.argument("player", EntityArgument.player())
                        .then(Commands.argument("weapon", com.mojang.brigadier.arguments.StringArgumentType.word())
                            .suggests((c, b) -> net.minecraft.commands.SharedSuggestionProvider.suggest(new String[]{"seraphic_blade", "abyssal_greatsword"}, b))
                            .executes(ctx -> {
                                ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                String id = com.mojang.brigadier.arguments.StringArgumentType.getString(ctx, "weapon");
                                net.minecraft.world.item.Item item = switch (id) {
                                    case "seraphic_blade" -> com.kuku.heavenhell.items.ModItems.SERAPHIC_BLADE;
                                    case "abyssal_greatsword" -> com.kuku.heavenhell.items.ModItems.ABYSSAL_GREATSWORD;
                                    default -> null;
                                };
                                if (item == null) { ctx.getSource().sendFailure(Component.literal("Unknown Sovereign weapon.")); return 0; }
                                net.minecraft.world.item.ItemStack reward = new net.minecraft.world.item.ItemStack(item);
                                if (!target.getInventory().add(reward)) target.drop(reward, false);
                                ctx.getSource().sendSuccess(() -> Component.literal("Granted " + id + " to " + target.getName().getString() + "."), true);
                                return 1;
                            })))));
'''
    if callback_end not in source:
        raise SystemExit("Could not find command callback insertion point")
    source = source.replace(callback_end, standalone + callback_end, 1)
path.write_text(source, encoding="utf-8")
print("Applied Sovereigns 1.21.11 API and standalone admin command fixes.")
