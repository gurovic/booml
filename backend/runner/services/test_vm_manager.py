import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from runner.services import vm_manager
from runner.services.vm_backends import LocalVmBackend
from runner.services.vm_config import get_vm_config
from runner.services.vm_manager import VmManager, sanitize_session_id


class VmManagerTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._tmp_dir = TemporaryDirectory()
        self.override = override_settings(
            RUNTIME_VM_ROOT=Path(self._tmp_dir.name),
            RUNTIME_VM_BACKEND="local",
            RUNTIME_VM_IMAGE="runner-vm:v0",
            RUNTIME_VM_CPU=2,
            RUNTIME_VM_RAM_MB=2048,
            RUNTIME_VM_DISK_GB=16,
            RUNTIME_VM_TTL_SEC=900,
            RUNTIME_VM_NET_OUTBOUND="deny",
            RUNTIME_VM_NET_ALLOWLIST=("https://example.com",),
        )
        self.override.enable()
        vm_manager.reset_vm_manager()

    def tearDown(self) -> None:
        vm_manager.reset_vm_manager()
        self.override.disable()
        self._tmp_dir.cleanup()
        super().tearDown()

    def test_ensure_session_vm_builds_local_workspace(self) -> None:
        manager = self._build_manager()

        vm = manager.ensure_session_vm("sess#1")

        self.assertEqual(vm.id, "runner-sess_1")
        self.assertTrue(vm.workspace_path.exists())
        metadata = self._read_metadata(manager.config.root_dir / vm.id)
        self.assertEqual(metadata["state"], "running")
        self.assertEqual(metadata["spec"]["image"], "runner-vm:v0")

    def test_overrides_apply_resources_and_network(self) -> None:
        manager = self._build_manager()

        vm = manager.ensure_session_vm(
            "sess-override",
            overrides={
                "image": "runner-vm:custom",
                "cpu": 4,
                "ram_mb": 8192,
                "disk_gb": 64,
                "ttl_sec": 1800,
                "net_outbound": "allow",
                "net_allowlist": ["https://one.example", "https://two.example"],
            },
        )

        self.assertEqual(vm.spec.image, "runner-vm:custom")
        self.assertEqual(vm.spec.resources.cpu, 4)
        self.assertEqual(vm.spec.resources.ram_mb, 8192)
        self.assertEqual(vm.spec.resources.disk_gb, 64)
        self.assertEqual(vm.spec.ttl_sec, 1800)
        self.assertEqual(vm.spec.network.outbound, "allow")
        self.assertEqual(
            vm.spec.network.allowlist, ("https://one.example", "https://two.example")
        )

    def test_destroy_session_vm_removes_directory(self) -> None:
        manager = self._build_manager()
        vm = manager.ensure_session_vm("sess-destroy")
        target_dir = vm.workspace_path.parent
        self.assertTrue(target_dir.exists())

        manager.destroy_session_vm("sess-destroy")

        self.assertFalse(target_dir.exists())

    def test_sanitize_session_id(self) -> None:
        self.assertEqual(sanitize_session_id("abc$#1"), "abc__1")
        self.assertEqual(sanitize_session_id("тест"), "____")

    def _build_manager(self) -> VmManager:
        config = get_vm_config()
        backend = LocalVmBackend(config.root_dir)
        return VmManager(config=config, backend=backend)

    def _read_metadata(self, vm_dir: Path) -> dict:
        metadata_path = vm_dir / "metadata.json"
        self.assertTrue(metadata_path.exists())
        return json.loads(metadata_path.read_text())
