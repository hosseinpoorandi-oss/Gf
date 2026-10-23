# WinRescue - bootable Windows wipe / repair tool

Debian-based live ISO (BIOS + UEFI hybrid). Boots from USB, installs nothing on the PC.

## 1. Build the ISO (on any Debian/Ubuntu x86_64 machine, needs internet, ~10-20 min)
    sudo ./build.sh            # produces WinRescue.iso + WinRescue.iso.sha256
No Linux? Use Docker (Windows/macOS/Linux):
    docker run --rm --privileged -v "$PWD":/w -w /w debian:bookworm bash -c "apt-get update && apt-get install -y sudo && ./build.sh"

## 2. Make the USB (any other working PC; USB gets erased)
- Windows: Rufus -> select WinRescue.iso -> when asked, choose **DD Image mode**.
  (balenaEtcher also works.)
- Linux: `sudo dd if=WinRescue.iso of=/dev/sdX bs=4M status=progress conv=fsync`  (double-check sdX!)

## 3. Boot it
Plug the USB into the broken PC, open the boot menu (F12 / F10 / Esc / F8 - varies), pick the USB.
**Disable Secure Boot** in firmware first if the USB doesn't appear (the wipe tool sends you to firmware anyway, so you can re-enable it before installing Windows).
Emergency shell: Ctrl+Alt+F2 (user `user`, password `live`).

## What each button does
**Full Windows Wipe** - choose a disk, type WIPE; removes all partition tables and filesystem signatures and zeroes the start/end of the disk (C:, EFI, MSR, Recovery all gone, disk unallocated); then reboots into firmware setup (UEFI). This is NOT a secure erase - data could be recovered with forensic tools.
**Smart Windows Repair** - fixes NTFS flags, validates registry hives (restores from RegBack if possible), quarantines zero-byte system binaries, clears a stuck pending update, restores bootmgfw.efi, reports BCD, measures reclaimable junk; if C: looks abnormal it asks before cleaning temp/cache/dump files; then sets Windows as next boot and reboots.

## Honest limits
Linux cannot run SFC/DISM, rebuild a missing BCD, or reliably detect malware. If repair reports FAIL for core files, use Windows Recovery (Reset this PC) or the Wipe option. Repair removes the hibernation file (hiberfil.sys) so the volume can be written.

## Boot modes
- **Normal mode** - safe GPU parameters (nomodeset, nouveau blacklisted). GUI tries auto-detect, then fbdev, then vesa.
- **Ultra Fail-Safe** - adds noapic/nolapic/acpi=off/irqpoll. Use only if Normal hangs. Reboot/poweroff may not work in this mode; hold the power button if needed.
- **Text mode only** - no graphics; same Wipe/Repair functions in a menu. Also used automatically if every GUI attempt fails.
- Xorg logs of each attempt: /run/wr/x-*.log (Ctrl+Alt+F2 for a shell).
- If the disk is not listed: set SATA mode to AHCI in firmware (Intel RST/VMD "RAID" mode hides disks). BitLocker-encrypted C: cannot be repaired from here (wipe still works).
