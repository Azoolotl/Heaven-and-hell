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
