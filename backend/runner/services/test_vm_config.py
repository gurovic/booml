from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from runner.services.vm_config import get_vm_config


class VmConfigTests(SimpleTestCase):
    def test_auto_backend_without_docker_uses_local(self) -> None:
        with override_settings(RUNTIME_VM_BACKEND="auto", RUNTIME_VM_ROOT=None):
            with patch("runner.services.vm_config.shutil.which", return_value=None):
                config = get_vm_config()
        self.assertEqual(config.backend, "local")
        self.assertTrue(config.root_dir.is_absolute())
        self.assertEqual(config.root_dir, settings.BASE_DIR / "media" / "notebook_sessions")

    def test_auto_backend_with_docker_prefers_docker(self) -> None:
        fake_root = Path(settings.BASE_DIR) / "custom_sessions"
        with override_settings(RUNTIME_VM_BACKEND="auto", RUNTIME_VM_ROOT=fake_root):
            with patch("runner.services.vm_config.shutil.which", return_value="/usr/bin/docker"):
                config = get_vm_config()
        self.assertEqual(config.backend, "docker")
        self.assertEqual(config.root_dir, fake_root.resolve())

    def test_allowlist_string_is_normalized(self) -> None:
        with override_settings(
            RUNTIME_VM_BACKEND="local",
            RUNTIME_VM_NET_ALLOWLIST="https://one.example, https://two.example , ",
        ):
            config = get_vm_config()
        self.assertEqual(config.net_allowlist, ("https://one.example", "https://two.example"))
