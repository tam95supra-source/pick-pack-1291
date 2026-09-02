#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")

activity=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
meal=read("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
old=read("app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt")
ui=read("app/src/main/java/vn/pickpack1291/app/beta/ReviewAlertUi.kt")

# Exactly one visual contract for reconciliation/warnings.
for token in ["HEIGHT_DP=42","RADIUS_DP=10","STROKE_DP=2","TEXT_SP=10.5f",
              "Tone.OK->Color.rgb(16,112,66)","Tone.WARNING->Color.rgb(176,0,32)",
              "Tone.OK->Color.rgb(226,248,235)","Tone.WARNING->Color.rgb(255,226,232)",
              "includeFontPadding=false","stateListAnimator=null","minimumHeight=0","minimumWidth=0"]:
    assert token in ui, token

# All relevant surfaces must call the shared component instead of defining their own alert style.
assert "ReviewAlertUi.button" in activity
assert "ReviewAlertUi.warningContainer(this)" in activity
assert "ReviewAlertUi.fixedHeightParams(this)" in activity
assert "ReviewAlertUi.warningContainer(activity)" in meal
assert 'ReviewAlertUi.button(activity,"",ReviewAlertUi.Tone.WARNING)' in meal
assert "ReviewAlertUi.fixedHeightParams(activity)" in meal
assert "ReviewAlertUi.warningContainer(activity)" in old
assert "ReviewAlertUi.button(activity,WARNING_TEXT,ReviewAlertUi.Tone.WARNING)" in old
assert "ReviewAlertUi.fixedHeightParams(activity)" in old

# Normal meal warning must not introduce a second orange visual language.
home=meal[meal.index("fun buildHomeWarning"):meal.index("fun build(activity")]
assert "Color.rgb(180,83,9)" not in home
assert "Color.rgb(255,247,237)" not in home
assert "val fg=" not in home and "val fill=" not in home

# Shift reconciliation keeps only two canonical states: OK green, warning red.
recon=activity[activity.index("private fun reconciliationButton"):activity.index("private fun host(")]
assert "ReviewAlertUi.Tone.OK" in recon
assert "ReviewAlertUi.Tone.WARNING" in recon
assert "GradientDrawable" not in recon

# Fixed geometry on every surface; no wrap-content warning buttons.
assert "ReviewAlertUi.HEIGHT_DP" in activity or "dp(42)" in activity
assert "LinearLayout.LayoutParams(-1,-2)" not in home
old_build=old[old.index("fun build("):old.index("var items=")]
assert "LinearLayout.LayoutParams(-1,-2)" not in old_build

print("beta112_review_warning_contract=PASS shared_component=PASS fixed_geometry=PASS warning_color=PASS review_tones=PASS no_platform_button_variance=PASS")
