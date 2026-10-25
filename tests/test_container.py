"""container.py's parsing against the Bash pipelines it replaces."""
import shutil
import subprocess
import unittest
from unittest import mock

from torquio import container

VULKANINFO = """==========
VULKANINFO
==========
Devices:
========
GPU0:
	apiVersion         = 1.4.311
	deviceType         = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
	deviceName         = Intel(R) Iris(R) Xe Graphics (TGL GT2)
GPU1:
	deviceType         = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
	deviceName         = NVIDIA GeForce RTX 4060 Laptop GPU = with an equals sign
GPU2:
	deviceType         = PHYSICAL_DEVICE_TYPE_CPU
	deviceName         = llvmpipe (LLVM 19.1.1, 256 bits)
"""
LIST_VULKAN_GPUS = """awk -F' = ' '/deviceType/ {t=$2} /deviceName/ {print t "|" $2}' | grep -v '^PHYSICAL_DEVICE_TYPE_CPU'"""

LISTINGS = [
    "ID           | NAME                 | STATUS             | IMAGE\nabc | torquio-env | Up 2 hours | x\n",
    "ID | NAME | STATUS | IMAGE\nabc | torquio-env | Exited (0) 3 days ago | x\ndef | torquio-env-old | Up | y\n",
    "ID | NAME\nabc | torquio-env\n",
    "",
]


@unittest.skipUnless(shutil.which("bash") and shutil.which("awk"), "needs bash and awk")
class ContainerMatchesBash(unittest.TestCase):
    def test_vulkan_gpus(self):
        expected = subprocess.run(["bash", "-c", LIST_VULKAN_GPUS], input=VULKANINFO, capture_output=True,
                                  text=True).stdout.splitlines()
        with mock.patch.object(container.run, "capture", return_value=(0, VULKANINFO)):
            self.assertEqual(container.vulkan_gpus(), expected)

    def test_status(self):
        for listing in LISTINGS:
            with self.subTest(listing=listing):
                expected = subprocess.run(
                    ["bash", "-c", """printf '%s' "$1" | grep torquio-env | awk -F'|' '{print $3}' | xargs""", "bash",
                     listing], capture_output=True, text=True).stdout.rstrip("\n")
                self.assertEqual(container.status(listing), expected)


if __name__ == "__main__":
    unittest.main()
