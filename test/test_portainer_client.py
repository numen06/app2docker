import unittest
from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.portainer_client import PortainerClient


class FakePortainerClient(PortainerClient):
    def __init__(self):
        self.endpoint_id = 7
        self.calls = []
        self.stacks = [{"Id": 42, "Name": "demo", "EndpointId": 7}]
        self.stack_file = "services:\n  app:\n    image: repo/app:latest\n"
        self.delete_error = None
        self.services = [
            {
                "ID": "svc1",
                "Spec": {
                    "Name": "demo_app",
                    "Labels": {"app2docker.deploy.revision": "task-1"},
                    "TaskTemplate": {
                        "ContainerSpec": {"Image": "repo/app:latest@sha256:new"}
                    },
                },
            }
        ]

    def _request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if method == "GET" and endpoint == "/stacks":
            return list(self.stacks)
        if method == "GET" and endpoint == "/stacks/42":
            if not self.stacks:
                raise Exception("not found")
            return dict(self.stacks[0])
        if method == "GET" and endpoint == "/stacks/42/file":
            return {"StackFileContent": self.stack_file}
        if method == "PUT" and endpoint == "/stacks/42":
            return {}
        if method == "DELETE" and endpoint == "/stacks/42":
            if self.delete_error:
                raise self.delete_error
            self.stacks = []
            return {}
        if method == "GET" and endpoint == "/endpoints/7/docker/services":
            return list(self.services)
        raise AssertionError(f"Unexpected request: {method} {endpoint}")


class PortainerClientTests(unittest.TestCase):
    def test_update_stack_requests_pull_image(self):
        client = FakePortainerClient()

        result = client.update_stack(42, client.stack_file, stack_name="demo")

        put_calls = [call for call in client.calls if call[0] == "PUT"]
        self.assertEqual(len(put_calls), 1)
        payload = put_calls[0][2]["json"]
        self.assertTrue(payload["PullImage"])
        self.assertFalse(payload["Prune"])
        self.assertEqual(result["stack_id"], 42)
        self.assertEqual(result["stack_name"], "demo")
        self.assertTrue(result["pull_image"])

    def test_remove_stack_resolves_name_to_id_and_waits_until_gone(self):
        client = FakePortainerClient()

        result = client.remove_stack(stack_name="demo", interval=0)

        self.assertTrue(result["success"])
        self.assertTrue(result["deleted"])
        self.assertEqual(result["stack_id"], 42)
        self.assertIn(("DELETE", "/stacks/42", {"params": {"endpointId": 7}, "timeout": 30}), client.calls)

    def test_remove_stack_raises_when_delete_fails(self):
        client = FakePortainerClient()
        client.delete_error = Exception("boom")

        with self.assertRaises(Exception):
            client.remove_stack(stack_name="demo", interval=0)

    def test_inject_deploy_revision_only_for_non_digest_image_refs(self):
        content = """
services:
  latest:
    image: repo/app:latest
  implicit:
    image: repo/worker
  versioned:
    image: repo/api:v1
  pinned:
    image: repo/api@sha256:abc
"""

        rendered, injected, count = PortainerClient.inject_deploy_revision(
            content, "task-1"
        )
        parsed = yaml.safe_load(rendered)

        self.assertTrue(injected)
        self.assertEqual(count, 3)
        self.assertEqual(
            parsed["services"]["latest"]["deploy"]["labels"][
                "app2docker.deploy.revision"
            ],
            "task-1",
        )
        self.assertEqual(
            parsed["services"]["implicit"]["deploy"]["labels"][
                "app2docker.deploy.revision"
            ],
            "task-1",
        )
        self.assertEqual(
            parsed["services"]["versioned"]["deploy"]["labels"][
                "app2docker.deploy.revision"
            ],
            "task-1",
        )
        self.assertNotIn("deploy", parsed["services"]["pinned"])

    def test_deploy_stack_updates_existing_stack_with_revision_metadata(self):
        client = FakePortainerClient()

        result = client.deploy_stack("demo", client.stack_file, revision="task-1")

        self.assertTrue(result["success"])
        self.assertTrue(result["revision_injected"])
        self.assertEqual(result["revision_service_count"], 1)
        put_payload = [call for call in client.calls if call[0] == "PUT"][0][2]["json"]
        self.assertIn("app2docker.deploy.revision", put_payload["StackFileContent"])

    def test_verify_stack_services_reports_service_images(self):
        client = FakePortainerClient()

        result = client.verify_stack_services(
            "demo", expected_revision="task-1", min_revision_services=1
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["checked"])
        self.assertEqual(result["service_count"], 1)
        self.assertEqual(result["images"], ["repo/app:latest@sha256:new"])
        self.assertEqual(result["matching_revision_services"], 1)

    def test_verify_stack_services_fails_when_revision_is_missing(self):
        client = FakePortainerClient()
        client.services[0]["Spec"]["Labels"] = {}

        result = client.verify_stack_services(
            "demo", expected_revision="task-1", min_revision_services=1
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["missing_revision_count"], 1)


if __name__ == "__main__":
    unittest.main()
