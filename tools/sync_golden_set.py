"""
Skyrim Sentinel - Golden Set Sync Utility

Matches scanned DLL hashes with known plugin names in golden_set.json.
"""

import json
from pathlib import Path


def sync_golden_set() -> None:
    """Sync scan_results.json hashes into golden_set.json for known plugins."""
    root = Path(__file__).parent
    golden_path = root / "golden_set.json"
    scan_path = root / "scan_results.json"

    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)

    with open(scan_path, encoding="utf-8") as f:
        scan_results = json.load(f)

    # Create filename -> result map
    scan_map = {r["filename"].lower(): r for r in scan_results}

    # Heuristic mapping for plugin name -> filename (if not obvious)
    name_map = {
        "SSE Engine Fixes": "EngineFixes.dll",
        "powerofthree's Tweaks": "po3_Tweaks.dll",
        "powerofthree's Papyrus Extender": "po3_PapyrusExtender.dll",
        "Bug Fixes SSE": "BugFixesSSE.dll",
        "ConsoleUtilSSE": "ConsoleUtilSSE.dll",
        "More Informative Console": "MoreInformativeConsole.dll",
        "MCM Helper": "MCMHelper.dll",
        "Scaleform Translation++": "ScaleformTranslationPP.dll",
        "ENB Helper SE": "ENBHelperSE.dll",
        "Dynamic Animation Replacer": "DynamicAnimationReplacer.dll",  # Might be outdated by OAR, but check
        "RaceMenu": "skee64.dll",
        "Scrambled Bugs": "ScrambledBugs.dll",
        "Actor Limit Fix": "ActorLimitFix.dll",
        "Better Jumping SE": "BetterJumpingSE.dll",
        "JContainers SE": "JContainers64.dll",
        "Fuz Ro D-oh": "Fuz Ro D'oh.dll",
        "Spell Perk Item Distributor": "po3_SpellPerkItemDistributor.dll",
        "Improved Camera SE": "ImprovedCameraSE.dll",
        "moreHUD SE": "AHZmoreHUDPlugin.dll",
        "TrueHUD": "TrueHUD.dll",
        "Keyword Item Distributor": "po3_KeywordItemDistributor.dll",
        "Base Object Swapper": "po3_BaseObjectSwapper.dll",
        "Backported Extended ESL Support": "BackportedESLSupport.dll",
        "Address Library for SKSE Plugins": None,  # No DLL usually, just database
        "Show Player In Menus": "ShowPlayerInMenus.dll",
        "Animation Motion Revolution": "AnimationMotionRevolution.dll",
        "Paired Animation Improvements": "PairedAnimationImprovements.dll",
        "Open Animation Replacer": "OpenAnimationReplacer.dll",
        "FSMP - Faster HDT-SMP": "hdtSMP64.dll",
        "CBPC - Physics with Collisions": "cbp.dll",
        "Crash Logger SSE AE VR": "CrashLogger.dll",
        "SSE Display Tweaks": "SSEDisplayTweaks.dll",
        "QuickLoot IE": "QuickLootIE.dll",
        "Immersive Equipment Displays": "ImmersiveEquipmentDisplays.dll",
        "Infinity UI": "InfinityUI.dll",
        "SkyPatcher": "SkyPatcher.dll",
        "Compass Navigation Overhaul": "CompassNavigationOverhaul.dll",
        "PrivateProfileRedirector SE": "PrivateProfileRedirector.dll",
        "Simple Dual Sheath": "SimpleDualSheath.dll",
        "Dismembering Framework": "DismemberingFramework.dll",
        "FormList Manipulator": "FormListManipulator.dll",
        "Sound Record Distributor": "SoundRecordDistributor.dll",
        "Inventory Interface Information Injector": "InventoryInjector.dll",
        "Simple Beheading NG": "SimpleBeheading.dll",
        "Papyrus Tweaks NG": "PapyrusTweaks.dll",
        "moreHUD Inventory Edition": "AHZmoreHUDInventory.dll",
        "ConsoleUtilSSE NG": "ConsoleUtilSSE.dll",
        "Better Third Person Selection": "BetterThirdPersonSelection.dll",
        "Animation Queue Fix": "AnimationQueueFix.dll",
        "Recursion Monitor": "RecursionFPSFix.dll",
        "ConsolePlusPlus": "po3_ConsolePlusPlus.dll",
        "MFG Fix NG": "mfgfix.dll",
        "Contextual Crosshair": "ContextualCrosshair.dll",
        "Grass Sampler Fix": "GrassSamplerFix.dll",
        "HeadpartWhitelist": "po3_HeadpartWhitelist.dll",
        "PhotoMode": "po3_PhotoMode.dll",
        "Modex": "Modex.dll",
        "ENB Input Disabler": "ENBInputDisabler.dll",
    }

    updated_count = 0

    for plugin in golden["plugins"]:
        # Skip if already verified (has file with sha256)
        if plugin.get("files") and any(f.get("sha256") for f in plugin["files"]):
            continue

        target_dll = name_map.get(plugin["name"])
        matched_result = None

        if target_dll:
            matched_result = scan_map.get(target_dll.lower())
        else:
            # Fallback: exact match filename?
            # Or try basic name matching
            pass

        if matched_result:
            plugin["files"] = [
                {
                    "filename": matched_result["filename"],
                    "sha256": matched_result["sha256"],
                    "size_bytes": matched_result["size_bytes"],
                    "status": "verified",
                }
            ]
            print(f"Matched: {plugin['name']} -> {matched_result['filename']}")
            updated_count += 1

    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(golden, f, indent=2)

    print(f"Updated {updated_count} plugins with verified hashes.")


if __name__ == "__main__":
    sync_golden_set()
