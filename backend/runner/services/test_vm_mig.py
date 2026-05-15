from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from runner.services.vm_backends import MIG_UUID_LABEL, DockerVmBackend
from runner.services.vm_exceptions import GpuSlotsBusy
from runner.services.vm_models import VmNetworkPolicy, VmResources, VmSpec


def _make_completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def _make_spec(*, gpu: bool) -> VmSpec:
    return VmSpec(
        image="runner-vm:test",
        resources=VmResources(cpu=1, ram_mb=512, disk_gb=4),
        network=VmNetworkPolicy(outbound="deny", allowlist=()),
        ttl_sec=900,
        gpu=gpu,
    )


class MigSelectionTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _backend(self, uuids: tuple[str, ...]) -> DockerVmBackend:
        return DockerVmBackend(self.root, gpu_mig_uuids=uuids)

    def test_pick_returns_first_when_pool_unused(self) -> None:
        backend = self._backend(("MIG-aaa", "MIG-bbb", "MIG-ccc"))
        with patch.object(backend, "_run_docker_capture", return_value=_make_completed(stdout="")):
            self.assertEqual(backend._pick_free_mig_uuid(), "MIG-aaa")

    def test_pick_skips_used_uuids(self) -> None:
        backend = self._backend(("MIG-aaa", "MIG-bbb", "MIG-ccc"))
        ps_output = (
            f"{MIG_UUID_LABEL}=MIG-aaa,com.docker.compose.project=booml\n"
            f"com.docker.compose.project=booml,{MIG_UUID_LABEL}=MIG-bbb\n"
        )
        with patch.object(backend, "_run_docker_capture", return_value=_make_completed(stdout=ps_output)):
            self.assertEqual(backend._pick_free_mig_uuid(), "MIG-ccc")

    def test_pick_raises_when_pool_exhausted(self) -> None:
        backend = self._backend(("MIG-aaa", "MIG-bbb"))
        ps_output = (
            f"{MIG_UUID_LABEL}=MIG-aaa\n"
            f"{MIG_UUID_LABEL}=MIG-bbb\n"
        )
        with patch.object(backend, "_run_docker_capture", return_value=_make_completed(stdout=ps_output)):
            with self.assertRaises(GpuSlotsBusy):
                backend._pick_free_mig_uuid()

    def test_list_ignores_irrelevant_labels(self) -> None:
        backend = self._backend(("MIG-aaa",))
        ps_output = (
            "other.label=foo,unrelated=bar\n"
            f"{MIG_UUID_LABEL}=MIG-zzz\n"
            "\n"
        )
        with patch.object(backend, "_run_docker_capture", return_value=_make_completed(stdout=ps_output)):
            self.assertEqual(backend._list_used_mig_uuids(), {"MIG-zzz"})

    def test_list_returns_empty_when_docker_call_fails(self) -> None:
        backend = self._backend(("MIG-aaa",))
        with patch.object(backend, "_run_docker_capture", return_value=_make_completed(returncode=1)):
            self.assertEqual(backend._list_used_mig_uuids(), set())

    def test_create_container_uses_specific_mig_device(self) -> None:
        backend = self._backend(("MIG-aaa", "MIG-bbb"))
        captured_args: list[tuple[str, ...]] = []

        def fake_run(args: tuple[str, ...], *, check: bool = True):
            captured_args.append(args)
            return _make_completed()

        vm_dir = self.root / "vm_test"
        vm_dir.mkdir()
        workspace = vm_dir / "workspace"
        workspace.mkdir()

        with patch.object(backend, "_run_docker", side_effect=fake_run), \
             patch.object(backend, "_run_docker_capture", return_value=_make_completed(stdout="")):
            chosen = backend._create_container("vm_test", _make_spec(gpu=True), vm_dir, workspace)

        self.assertEqual(chosen, "MIG-aaa")
        create_args = next(args for args in captured_args if args and args[0] == "create")
        self.assertIn("--label", create_args)
        self.assertIn(f"{MIG_UUID_LABEL}=MIG-aaa", create_args)
        self.assertIn("--gpus", create_args)
        self.assertIn("device=MIG-aaa", create_args)
        # Should NOT also include the legacy "all" flag.
        self.assertNotIn("all", create_args)

    def test_create_container_falls_back_to_gpus_all_when_no_pool(self) -> None:
        backend = self._backend(())  # no MIG configured
        captured_args: list[tuple[str, ...]] = []

        def fake_run(args: tuple[str, ...], *, check: bool = True):
            captured_args.append(args)
            return _make_completed()

        vm_dir = self.root / "vm_legacy"
        vm_dir.mkdir()
        workspace = vm_dir / "workspace"
        workspace.mkdir()

        with patch.object(backend, "_run_docker", side_effect=fake_run):
            chosen = backend._create_container("vm_legacy", _make_spec(gpu=True), vm_dir, workspace)

        self.assertIsNone(chosen)
        create_args = next(args for args in captured_args if args and args[0] == "create")
        self.assertIn("--gpus", create_args)
        self.assertIn("all", create_args)
        # No MIG label.
        for arg in create_args:
            self.assertFalse(arg.startswith(f"{MIG_UUID_LABEL}="), arg)

    def test_create_container_omits_gpu_flags_for_cpu_spec(self) -> None:
        backend = self._backend(("MIG-aaa",))
        captured_args: list[tuple[str, ...]] = []

        def fake_run(args: tuple[str, ...], *, check: bool = True):
            captured_args.append(args)
            return _make_completed()

        vm_dir = self.root / "vm_cpu"
        vm_dir.mkdir()
        workspace = vm_dir / "workspace"
        workspace.mkdir()

        with patch.object(backend, "_run_docker", side_effect=fake_run):
            chosen = backend._create_container("vm_cpu", _make_spec(gpu=False), vm_dir, workspace)

        self.assertIsNone(chosen)
        create_args = next(args for args in captured_args if args and args[0] == "create")
        self.assertNotIn("--gpus", create_args)
