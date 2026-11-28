from pathlib import Path
import sys

root = Path(sys.argv[1])
item = root / "src/main/java/com/kuku/heavenhell/items/RelicItem.java"
s = item.read_text(encoding="utf-8")
old_import = "import net.minecraft.world.item.TooltipFlag;\n"
if "import net.minecraft.world.item.component.TooltipDisplay;" not in s:
    if old_import not in s:
        raise SystemExit("RelicItem TooltipFlag import not found")
    s = s.replace(old_import, old_import + "import net.minecraft.world.item.component.TooltipDisplay;\nimport java.util.function.Consumer;\n", 1)
old_sig = "public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {"
new_sig = "public void appendHoverText(ItemStack stack, Item.TooltipContext context, TooltipDisplay display, Consumer<Component> textConsumer, TooltipFlag flag) {"
if old_sig in s:
    s = s.replace(old_sig, new_sig, 1)
elif new_sig not in s:
    raise SystemExit("RelicItem tooltip method signature not found")
s = s.replace('tooltip.add(Component.translatable("item.heavenhell." + relicId + ".desc"));',
              'textConsumer.accept(Component.translatable("item.heavenhell." + relicId + ".desc"));', 1)
item.write_text(s, encoding="utf-8")

manager = root / "src/main/java/com/kuku/heavenhell/gameplay/RelicManager.java"
s = manager.read_text(encoding="utf-8")
old = """        return data != null && relicId != null
                && (relicId.equals(data.relicSlotOne) || relicId.equals(data.relicSlotTwo));"""
new = """        return data != null && relicId != null && data.race != Race.HUMAN && !data.isPowerless()
                && (relicId.equals(data.relicSlotOne) || relicId.equals(data.relicSlotTwo));"""
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("Relic eligibility guard anchor not found")
manager.write_text(s, encoding="utf-8")
print("Fixed Minecraft 1.21.11 relic tooltip API and disabled relic modifiers for unpowered players.")
