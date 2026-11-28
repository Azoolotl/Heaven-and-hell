#!/usr/bin/env python3
"""Compatibility and command-structure fixes for Sovereigns on Minecraft 1.21.11."""
from pathlib import Path
import sys

root = Path(sys.argv[1])

weapon = "src/main/java/com/kuku/heavenhell/gameplay/SovereignWeaponService.java"
weapon_path = root / weapon
weapon_source = weapon_path.read_text(encoding="utf-8")
weapon_source = weapon_source.replace("import net.minecraft.core.registries.BuiltInRegistries;\n", "")
weapon_source = weapon_source.replace("import net.minecraft.world.item.ItemStack;\n", "")
weapon_source = weapon_source.replace(
    "import net.minecraft.core.particles.ParticleTypes;\n",
    "import net.minecraft.core.particles.ParticleTypes;\nimport net.minecraft.world.item.ItemStack;\n")
old_check_a = "        if (serverPlayer.getCooldowns().isOnCooldown(item)) {"
old_check_b = "        if (serverPlayer.getCooldowns().isOnCooldown(BuiltInRegistries.ITEM.getKey(item))) {"
new_check = ("        ItemStack weaponStack = serverPlayer.getMainHandItem().is(item) ? serverPlayer.getMainHandItem() : serverPlayer.getOffhandItem();\n"
             "        if (serverPlayer.getCooldowns().isOnCooldown(weaponStack)) {")
if old_check_a in weapon_source:
    weapon_source = weapon_source.replace(old_check_a, new_check, 1)
elif old_check_b in weapon_source:
    weapon_source = weapon_source.replace(old_check_b, new_check, 1)
elif new_check not in weapon_source:
    raise SystemExit("cooldown lookup stack: expected source pattern was not found")
weapon_source = weapon_source.replace("getCooldowns().addCooldown(item, cooldown)", "getCooldowns().addCooldown(weaponStack, cooldown)")
weapon_source = weapon_source.replace(
    "getCooldowns().addCooldown(BuiltInRegistries.ITEM.getKey(item), cooldown)",
    "getCooldowns().addCooldown(weaponStack, cooldown)")
weapon_source = weapon_source.replace("ServerLevel level = serverPlayer.serverLevel();", "ServerLevel level = (ServerLevel) serverPlayer.level();")
weapon_source = weapon_source.replace("impact.owner.serverLevel() != impact.level", "impact.owner.level() != impact.level")
weapon_source = weapon_source.replace("this.level = owner.serverLevel();", "this.level = (ServerLevel) owner.level();")
weapon_source = weapon_source.replace(
    "impact.level.sendParticles(impact.holy ? ParticleTypes.FLASH : ParticleTypes.EXPLOSION,",
    "impact.level.sendParticles(ParticleTypes.EXPLOSION,")
weapon_path.write_text(weapon_source, encoding="utf-8")

boss = "src/main/java/com/kuku/heavenhell/gameplay/SovereignBossService.java"
boss_path = root / boss
boss_source = boss_path.read_text(encoding="utf-8")
boss_source = boss_source.replace(
    "boss.moveTo(position.x, position.y, position.z, level.random.nextFloat() * 360.0f, 0.0f);",
    "boss.setPos(position.x, position.y, position.z);")
boss_source = boss_source.replace(
    "impact.level.sendParticles(impact.holy ? ParticleTypes.FLASH : ParticleTypes.EXPLOSION,",
    "impact.level.sendParticles(ParticleTypes.EXPLOSION,")
boss_path.write_text(boss_source, encoding="utf-8")

# Put the sovereign admin commands in separate roots so they do not interfere
# with the existing /heavenhell command tree.
commands_path = root / "src/main/java/com/kuku/heavenhell/command/HeavenHellCommands.java"
commands = commands_path.read_text(encoding="utf-8")
start_marker = '                .then(Commands.literal("boss").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))'
end_marker = '                .then(Commands.literal("reload")'
start = commands.find(start_marker)
if start >= 0:
    end = commands.find(end_marker, start)
    if end < 0:
        raise SystemExit("Could not find /heavenhell reload branch after Sovereigns admin commands")
    commands = commands[:start] + commands[end:]
callback_end = '        });\n    }\n    private static void showKarma'
if 'Commands.literal("heavenhellboss")' not in commands:
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
    if callback_end not in commands:
        raise SystemExit("Could not find command callback insertion point")
    commands = commands.replace(callback_end, standalone + callback_end, 1)
commands_path.write_text(commands, encoding="utf-8")
print("Applied Sovereigns 1.21.11 API and standalone admin command fixes.")
