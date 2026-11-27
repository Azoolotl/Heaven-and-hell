from pathlib import Path
import sys

project = Path(sys.argv[1] if len(sys.argv) > 1 else "project/heaven-hell-fabric")
path = project / "src/main/java/com/kuku/heavenhell/gameplay/AwakeningService.java"
text = path.read_text(encoding="utf-8")

old_import = "import net.minecraft.core.particles.ParticleTypes;\n"
new_import = "import net.minecraft.core.particles.ColorParticleOption;\n" + old_import
if old_import in text and "import net.minecraft.core.particles.ColorParticleOption;" not in text:
    text = text.replace(old_import, new_import, 1)
elif "import net.minecraft.core.particles.ColorParticleOption;" not in text:
    raise SystemExit("AwakeningService particle import anchor not found")

old_flash = "level.sendParticles(ParticleTypes.FLASH, player.getX(), player.getY() + 1.0, player.getZ(), 1, 0, 0, 0, 0);"
new_flash = "level.sendParticles(ColorParticleOption.create(ParticleTypes.FLASH, 0xFFFFFF), player.getX(), player.getY() + 1.0, player.getZ(), 1, 0, 0, 0, 0);"
if old_flash in text:
    if text.count(old_flash) != 1:
        raise SystemExit("Unexpected number of Awakening FLASH calls")
    text = text.replace(old_flash, new_flash, 1)
elif new_flash not in text:
    raise SystemExit("Awakening FLASH call anchor not found")

path.write_text(text, encoding="utf-8")
print("Applied Minecraft 1.21.11 Awakening FLASH particle compatibility fix.")
