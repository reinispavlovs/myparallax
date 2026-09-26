import shutil
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(".").resolve()
TARGET = REPO_ROOT / "megaliths-cosmology.html"

# --- Backup first ---
backup_dir = REPO_ROOT / "_archive" / "frontend_backups"
backup_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup_path = backup_dir / f"megaliths-cosmology.html.bak.{ts}"
shutil.copy2(TARGET, backup_path)
print(f"[OK] Backed up -> {backup_path.relative_to(REPO_ROOT)}")

text = TARGET.read_text(encoding="utf-8")

# --- Replacement 1: Barabar sentence (appears twice: inline HTML + i18n dict) ---
old_barabar = "These chambers possess extreme acoustic resonance capable of inducing deep psychoacoustic effects on consciousness through the piezoelectric granite composition."
new_barabar = "These chambers exhibit strong acoustic resonance; some researchers have speculatively proposed a link between the granite's piezoelectric quartz content and psychoacoustic effects, though this remains unverified and outside mainstream acoustic engineering consensus."

count_barabar = text.count(old_barabar)
print(f"[CHECK] Barabar sentence occurrences found: {count_barabar} (expected: 2)")

# --- Replacement 2: Tiwanaku metaphysics EN ---
old_tiwa_en = "Piezoelectric quartz composition creates localized electromagnetic anomalies stimulating the pineal gland and spatial perception."
new_tiwa_en = "Piezoelectric quartz composition is hypothesized by fringe researchers to create localized electromagnetic anomalies that may stimulate the pineal gland and spatial perception \u2014 a speculative claim with no empirical verification."

count_tiwa_en = text.count(old_tiwa_en)
print(f"[CHECK] Tiwanaku EN occurrences found: {count_tiwa_en} (expected: 1)")

# --- Replacement 3: Tiwanaku metaphysics LV ---
old_tiwa_lv = "Piezoelektriskais kvarcs andes\u012bt\u0101 rada sp\u0113c\u012bgas elektromagn\u0113tisk\u0101 lauka anom\u0101lijas, stimul\u0113jot epif\u012bzi un telpas uztveri."
new_tiwa_lv = "Piezoelektriskais kvarcs andes\u012bt\u0101 tiek spekulat\u012bvi saist\u012bts ar elektromagn\u0113tisk\u0101 lauka anom\u0101lij\u0101m, kas var\u0113tu ietekm\u0113t epif\u012bzi un telpas uztveri \u2013 \u0161is apgalvojums nav emp\u012briski pier\u0101d\u012bts."

count_tiwa_lv = text.count(old_tiwa_lv)
print(f"[CHECK] Tiwanaku LV occurrences found: {count_tiwa_lv} (expected: 1)")

print()
if count_barabar == 2 and count_tiwa_en == 1 and count_tiwa_lv == 1:
    text = text.replace(old_barabar, new_barabar)
    text = text.replace(old_tiwa_en, new_tiwa_en)
    text = text.replace(old_tiwa_lv, new_tiwa_lv)
    TARGET.write_text(text, encoding="utf-8")
    print("[OK] All 4 replacements applied successfully. File written.")
else:
    print("[ABORT] Occurrence counts did not match expectations. NO changes written.")
    print("        Inspect the file manually -- exact string mismatch (whitespace/quotes/dash chars).")
