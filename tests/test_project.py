# SPDX-License-Identifier: GPL-2.0-only
"""Meaningful verification of boot-file safety using disposable fixtures only."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from collect import redact
from fdt import read_fdt
from install import prepare_install, apply_plan
from verify import sha256, settings, verify_delta


class InstallSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.boot = Path(self.temp.name)
        dtb_dir = self.boot/'dtb/amlogic'
        dtb_dir.mkdir(parents=True)
        self.cfg = settings()
        # Use the actual rescue binary as the fixture, not a synthetic toy DT.
        self.rescue = dtb_dir/self.cfg['rescue_name']
        self.rescue.write_bytes(self.baseline)
        self.config = self.boot/'uEnv.txt'
        self.original = b'LINUX=/zImage\nINITRD=/uInitrd\nFDT=/dtb/amlogic/meson-sm1-x96-max-plus-100m.dtb\nAPPEND=root=UUID=TEST-ROOT rootwait console=ttyAML0,115200n8\n'
        self.config.write_bytes(self.original)
        self.original_mode = self.config.stat().st_mode & 0o777

    @classmethod
    def setUpClass(cls):
        cfg = settings()
        cls.baseline = (ROOT / cfg['reference_binary']).read_bytes()
        if sha256(cls.baseline) != cfg['base_sha256']:
            raise RuntimeError('Exact baseline fixture checksum mismatch')

    def tearDown(self):
        self.temp.cleanup()

    def test_install_changes_only_fdt_and_keeps_rescue_backup(self):
        plan=prepare_install(self.boot,self.cfg['tested_kernel'])
        with patch('install.os.sync'):
            apply_plan(plan)
        self.assertEqual(self.rescue.read_bytes(),self.baseline)
        self.assertEqual(plan.backup.read_bytes(),self.original)
        self.assertEqual(self.config.read_bytes(),self.original.replace(self.cfg['rescue_name'].encode(),self.cfg['candidate_name'].encode()))
        self.assertEqual(self.config.stat().st_mode & 0o777,self.original_mode)
        self.assertTrue(prepare_install(self.boot,self.cfg['tested_kernel']).already_installed)

    def test_wrong_kernel_and_baseline_are_rejected_without_writes(self):
        with self.assertRaises(ValueError): prepare_install(self.boot,'other-kernel')
        self.rescue.write_bytes(b'not the baseline')
        with self.assertRaises(ValueError): prepare_install(self.boot,self.cfg['tested_kernel'])
        self.assertEqual(self.config.read_bytes(),self.original)
        self.assertFalse((self.boot/'uEnv.txt.n5max-backup').exists())

    def test_multiple_fdt_and_extlinux_rejected(self):
        self.config.write_bytes(self.original+b'FDT=/another.dtb\n')
        with self.assertRaises(ValueError): prepare_install(self.boot,self.cfg['tested_kernel'])
        self.config.write_bytes(self.original)
        (self.boot/'extlinux').mkdir()
        (self.boot/'extlinux/extlinux.conf').write_text('DEFAULT linux\n')
        with self.assertRaises(ValueError): prepare_install(self.boot,self.cfg['tested_kernel'])

    def test_different_backup_is_preserved(self):
        backup=self.boot/'uEnv.txt.n5max-backup'
        backup.write_bytes(b'older backup')
        with self.assertRaises(ValueError): prepare_install(self.boot,self.cfg['tested_kernel'])
        self.assertEqual(backup.read_bytes(),b'older backup')

    def test_target_symlink_and_hardlink_cannot_overwrite_rescue(self):
        target=self.boot/'dtb/amlogic'/self.cfg['candidate_name']
        target.symlink_to(self.rescue)
        with self.assertRaises(ValueError): prepare_install(self.boot,self.cfg['tested_kernel'])
        target.unlink()
        os.link(self.rescue,target)
        with self.assertRaises(ValueError): prepare_install(self.boot,self.cfg['tested_kernel'])
        self.assertEqual(self.rescue.read_bytes(),self.baseline)

    def test_plan_invalidated_by_config_change(self):
        plan=prepare_install(self.boot,self.cfg['tested_kernel'])
        changed=self.original.replace(b'rootwait',b'rootwait quiet')
        self.config.write_bytes(changed)
        with self.assertRaises(ValueError): apply_plan(plan)
        self.assertEqual(self.config.read_bytes(),changed)
        self.assertFalse(plan.backup.exists())

    def test_failed_dtb_write_never_selects_candidate(self):
        plan=prepare_install(self.boot,self.cfg['tested_kernel'])
        with patch('install.atomic_write',side_effect=OSError('simulated disk-full')):
            with self.assertRaises(OSError): apply_plan(plan)
        self.assertEqual(self.config.read_bytes(),self.original)
        self.assertEqual(self.rescue.read_bytes(),self.baseline)
        self.assertEqual(plan.backup.read_bytes(),self.original)

    def test_commented_example_does_not_steal_fdt_replacement(self):
        comment = b'# Example: FDT=/dtb/amlogic/meson-sm1-x96-max-plus-100m.dtb\n'
        self.config.write_bytes(comment + self.original)
        plan = prepare_install(self.boot, self.cfg['tested_kernel'])
        self.assertTrue(plan.after.startswith(comment))
        self.assertEqual(plan.after[len(comment):], self.original.replace(
            self.cfg['rescue_name'].encode(), self.cfg['candidate_name'].encode()))

    def test_crlf_preserved(self):
        crlf=self.original.replace(b'\n',b'\r\n')
        self.config.write_bytes(crlf)
        plan=prepare_install(self.boot,self.cfg['tested_kernel'])
        self.assertEqual(plan.after,crlf.replace(self.cfg['rescue_name'].encode(),self.cfg['candidate_name'].encode()))

    def test_ethernet_diff_gate_rejects_other_valid_tree(self):
        with self.assertRaises(ValueError): verify_delta(self.baseline,self.baseline)
        candidate=(ROOT/self.cfg['candidate']).read_bytes()
        self.assertEqual(verify_delta(self.baseline,candidate),(542,6))


class ParserAndPrivacy(unittest.TestCase):
    def test_truncated_fdt_rejected(self):
        with self.assertRaises(ValueError): read_fdt(b'\xd0\x0d\xfe\xed')

    def test_redaction_preserves_phy_id_and_kernel(self):
        sample='192.0.2.8/24 2001:db8:abcd::1 02:11:22:33:44:55 12345678-1234-1234-1234-123456789abc kernel 6.12.111-ophub PHY 0x01803301'
        text=redact(sample)
        for secret in ('192.0.2.8','2001:db8','02:11:22:33:44:55','12345678-1234'):
            self.assertNotIn(secret,text)
        self.assertIn('6.12.111-ophub',text)
        self.assertIn('0x01803301',text)


if __name__=='__main__': unittest.main()
