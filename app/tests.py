from .models import Output, Project, Stack, UsedBy
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import override_settings
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APITestCase
from typing import Any


class TestCase(APITestCase):
    maxDiff = None
    fixtures = ["sample.yaml"]

    def assertResponse(self, path: str, expected: Any, **kwargs):
        response = self.client.get(path, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, expected)


class BasicTest(TestCase):
    maxDiff = None
    fixtures = ["sample.yaml"]

    def test_consistency(self):
        # Two projects should not have the same slug
        p = Project.objects.create(name="Test", slug="test")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Project.objects.create(name="Test", slug="test")

        # Two stacks can only have the same slug if they are in different projects
        Stack.objects.create(name="test", slug="test", project_id=1)
        Stack.objects.create(name="test", slug="test", project_id=p.id)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Stack.objects.create(name="test", slug="test", project_id=p.id)

        # The slug should never be empty
        for Model in (Project, Stack):
            with self.assertRaises(ValidationError):
                Model(name="empty slug", slug="").clean_fields()
            with self.assertRaises(ValidationError):
                Model(name="empty slug", slug=None).clean_fields()

        # A stack cannot depend on itself
        with transaction.atomic(), self.assertRaises(IntegrityError):
            UsedBy.objects.create(stack_id=1, used_by_id=1, last_used_at=timezone.now())

        # A dependency can only exist once
        UsedBy.objects.create(stack_id=1, used_by_id=2, last_used_at=timezone.now())
        with transaction.atomic(), self.assertRaises(IntegrityError):
            UsedBy.objects.create(stack_id=1, used_by_id=2, last_used_at=timezone.now())

        # Outputs must have a name
        with self.assertRaises(ValidationError):
            Output(stack_id=1, value="test", deprecated="").clean_fields()
        Output(stack_id=1, key="test", value="test", deprecated=None).clean_fields()

        # Outputs must have a unique name in a given stack
        Output.objects.create(stack_id=1, key="test", value="test", deprecated="")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Output.objects.create(stack_id=1, key="test", value="test", deprecated="")

    def test_root(self):
        self.assertResponse(
            "/v1/",
            {
                "projects": "http://testserver/v1/projects/",
            },
        )


class TestProject(TestCase):
    def test_list_projects(self):
        self.assertResponse(
            "/v1/projects/",
            [
                {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                    "stacks": [
                        {
                            "id": "backend/load-balancers",
                            "name": "Load-Balancers",
                            "url": "http://testserver/v1/projects/backend/load-balancers/",
                        }
                    ],
                },
                {
                    "id": "frontend",
                    "name": "Frontend",
                    "stacks": [
                        {
                            "id": "frontend/dev",
                            "name": "Dev",
                            "url": "http://testserver/v1/projects/frontend/dev/",
                        },
                        {
                            "id": "frontend/staging",
                            "name": "Staging",
                            "url": "http://testserver/v1/projects/frontend/staging/",
                        },
                        {
                            "id": "frontend/prod",
                            "name": "Prod",
                            "url": "http://testserver/v1/projects/frontend/prod/",
                        },
                    ],
                    "url": "http://testserver/v1/projects/frontend/",
                },
            ],
        )

    def test_create_project(self):
        response = self.client.post("/v1/projects/", {"name": "Hello world"})
        self.assertEqual(response.status_code, 201)
        self.assertJSONEqual(
            response.content,
            {
                "id": "hello-world",
                "name": "Hello world",
                "stacks": [],
                "url": "http://testserver/v1/projects/hello-world/",
            },
        )
        self.assertResponse(
            "/v1/projects/",
            [
                {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                    "stacks": [
                        {
                            "id": "backend/load-balancers",
                            "name": "Load-Balancers",
                            "url": "http://testserver/v1/projects/backend/load-balancers/",
                        }
                    ],
                },
                {
                    "id": "frontend",
                    "name": "Frontend",
                    "stacks": [
                        {
                            "id": "frontend/dev",
                            "name": "Dev",
                            "url": "http://testserver/v1/projects/frontend/dev/",
                        },
                        {
                            "id": "frontend/staging",
                            "name": "Staging",
                            "url": "http://testserver/v1/projects/frontend/staging/",
                        },
                        {
                            "id": "frontend/prod",
                            "name": "Prod",
                            "url": "http://testserver/v1/projects/frontend/prod/",
                        },
                    ],
                    "url": "http://testserver/v1/projects/frontend/",
                },
                {
                    "id": "hello-world",
                    "name": "Hello world",
                    "stacks": [],
                    "url": "http://testserver/v1/projects/hello-world/",
                },
            ],
        )

    def test_read_project(self):
        self.assertResponse(
            "/v1/projects/backend/",
            {
                "id": "backend",
                "name": "Backend",
                "stacks": [
                    {
                        "id": "backend/load-balancers",
                        "name": "Load-Balancers",
                        "url": "http://testserver/v1/projects/backend/load-balancers/",
                    }
                ],
                "url": "http://testserver/v1/projects/backend/",
            },
        )
        response = self.client.get("/v1/projects/404/")
        self.assertEqual(response.status_code, 404)

    def test_update_project(self):
        self.client.put("/v1/projects/backend/", {"name": "Test"})
        self.assertResponse(
            "/v1/projects/backend/",
            {
                "id": "backend",
                "name": "Test",
                "stacks": [
                    {
                        "id": "backend/load-balancers",
                        "name": "Load-Balancers",
                        "url": "http://testserver/v1/projects/backend/load-balancers/",
                    }
                ],
                "url": "http://testserver/v1/projects/backend/",
            },
        )

    def test_destroy_project(self):
        self.client.delete("/v1/projects/frontend/")
        self.assertResponse(
            "/v1/projects/",
            [
                {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                    "stacks": [
                        {
                            "id": "backend/load-balancers",
                            "name": "Load-Balancers",
                            "url": "http://testserver/v1/projects/backend/load-balancers/",
                        }
                    ],
                },
            ],
        )


class TestStack(TestCase):
    def test_create_stack(self):
        response = self.client.post("/v1/projects/backend/", {"name": "Hello world"})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertJSONEqual(
            response.content,
            {
                "id": "backend/hello-world",
                "name": "Hello world",
                "outputs": {},
                "url": "http://testserver/v1/projects/backend/hello-world/",
                "project": {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                },
                "used_by": [],
            },
        )

        response = self.client.post(
            "/v1/projects/backend/",
            {"name": "Test with outputs", "outputs": {"foo": {"value": "bar"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertJSONEqual(
            response.content,
            {
                "id": "backend/test-with-outputs",
                "name": "Test with outputs",
                "outputs": {
                    "foo": {
                        "value": "bar",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                "url": "http://testserver/v1/projects/backend/test-with-outputs/",
                "project": {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                },
                "used_by": [],
            },
        )

    def test_read_stack(self):
        self.assertResponse(
            "/v1/projects/frontend/dev/",
            {
                "id": "frontend/dev",
                "name": "Dev",
                "url": "http://testserver/v1/projects/frontend/dev/",
                "project": {
                    "id": "frontend",
                    "name": "Frontend",
                    "url": "http://testserver/v1/projects/frontend/",
                },
                "outputs": {
                    "url": {
                        "value": "https://my-dev-environment.bla",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                "used_by": [],
            },
        )
        response = self.client.get("/v1/projects/frontend/404/")
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/v1/projects/backend/dev/")
        self.assertEqual(response.status_code, 404)

    def test_update_stack(self):
        response = self.client.put(
            "/v1/projects/backend/load-balancers/", {"name": "Test"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertResponse(
            "/v1/projects/backend/load-balancers/",
            {
                "id": "backend/load-balancers",
                "name": "Test",
                "url": "http://testserver/v1/projects/backend/load-balancers/",
                "project": {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                },
                "outputs": {
                    "hostname": {
                        "value": "https://hello.eu-central-1.blabla",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                "used_by": [],
            },
        )

        response = self.client.put(
            "/v1/projects/backend/load-balancers/",
            {"name": "Test2", "outputs": {"hello": {"value": "world"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertResponse(
            "/v1/projects/backend/load-balancers/",
            {
                "id": "backend/load-balancers",
                "name": "Test2",
                "url": "http://testserver/v1/projects/backend/load-balancers/",
                "project": {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                },
                "outputs": {
                    "hostname": {
                        "value": "https://hello.eu-central-1.blabla",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                "used_by": [],
            },
        )

    def test_destroy_stack(self):
        response = self.client.delete("/v1/projects/frontend/dev/")
        self.assertEqual(response.status_code, 204)
        self.assertResponse(
            "/v1/projects/frontend/",
            {
                "id": "frontend",
                "name": "Frontend",
                "stacks": [
                    {
                        "id": "frontend/staging",
                        "name": "Staging",
                        "url": "http://testserver/v1/projects/frontend/staging/",
                    },
                    {
                        "id": "frontend/prod",
                        "name": "Prod",
                        "url": "http://testserver/v1/projects/frontend/prod/",
                    },
                ],
                "url": "http://testserver/v1/projects/frontend/",
            },
        )

        response = self.client.delete("/v1/projects/frontend/dev/")
        self.assertEqual(response.status_code, 404)


class TestOutput(TestCase):
    def test_read_outputs(self):
        self.assertResponse(
            "/v1/projects/backend/load-balancers/outputs/",
            {
                "hostname": {
                    "value": "https://hello.eu-central-1.blabla",
                    "deprecated": None,
                    "warning": None,
                    "sensitive": False,
                }
            },
        )
        self.assertResponse(
            "/v1/projects/backend/load-balancers/outputs/hostname/",
            {
                "value": "https://hello.eu-central-1.blabla",
                "deprecated": None,
                "warning": None,
                "sensitive": False,
            },
        )
        response = self.client.get("/v1/projects/backend/load-balancers/outputs/404/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.content, b'{"detail":"\'404\' is not present in the outputs."}'
        )
        response = self.client.get(
            "/v1/projects/backend/load-balancers/outputs/hostname/?format=raw"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"https://hello.eu-central-1.blabla")
        response = self.client.get("/v1/projects/frontend/404/outputs/")
        self.assertEqual(response.status_code, 404)
        response = self.client.get("/v1/projects/frontend/404/outputs/hello/")
        self.assertEqual(response.status_code, 404)

    def test_used_by(self):
        with freeze_time("2022-07-02") as ft:
            self.assertResponse(
                "/v1/projects/backend/load-balancers/outputs/",
                {
                    "hostname": {
                        "value": "https://hello.eu-central-1.blabla",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                HTTP_X_watson_STACK="frontend/dev",
            )
            self.assertResponse(
                "/v1/projects/backend/load-balancers/",
                {
                    "id": "backend/load-balancers",
                    "name": "Load-Balancers",
                    "url": "http://testserver/v1/projects/backend/load-balancers/",
                    "project": {
                        "id": "backend",
                        "name": "Backend",
                        "url": "http://testserver/v1/projects/backend/",
                    },
                    "outputs": {
                        "hostname": {
                            "value": "https://hello.eu-central-1.blabla",
                            "deprecated": None,
                            "warning": None,
                            "sensitive": False,
                        }
                    },
                    "used_by": [
                        {
                            "id": "frontend/dev",
                            "url": "http://testserver/v1/projects/frontend/dev/",
                            "last_used_at": "2022-07-02T00:00:00Z",
                        }
                    ],
                },
            )

            ft.tick()
            self.assertResponse(
                "/v1/projects/backend/load-balancers/outputs/",
                {
                    "hostname": {
                        "value": "https://hello.eu-central-1.blabla",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                HTTP_X_watson_STACK="frontend/dev",
            )
            self.assertResponse(
                "/v1/projects/backend/load-balancers/",
                {
                    "id": "backend/load-balancers",
                    "name": "Load-Balancers",
                    "url": "http://testserver/v1/projects/backend/load-balancers/",
                    "project": {
                        "id": "backend",
                        "name": "Backend",
                        "url": "http://testserver/v1/projects/backend/",
                    },
                    "outputs": {
                        "hostname": {
                            "value": "https://hello.eu-central-1.blabla",
                            "deprecated": None,
                            "warning": None,
                            "sensitive": False,
                        }
                    },
                    "used_by": [
                        {
                            "id": "frontend/dev",
                            "url": "http://testserver/v1/projects/frontend/dev/",
                            "last_used_at": "2022-07-02T00:00:01Z",
                        }
                    ],
                },
            )

    def test_used_by_self(self):
        self.assertResponse(
            "/v1/projects/backend/load-balancers/outputs/",
            {
                "hostname": {
                    "value": "https://hello.eu-central-1.blabla",
                    "deprecated": None,
                    "warning": None,
                    "sensitive": False,
                }
            },
            HTTP_X_watson_STACK="backend/load-balancers",
        )
        self.assertResponse(
            "/v1/projects/backend/load-balancers/",
            {
                "id": "backend/load-balancers",
                "name": "Load-Balancers",
                "url": "http://testserver/v1/projects/backend/load-balancers/",
                "project": {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                },
                "outputs": {
                    "hostname": {
                        "value": "https://hello.eu-central-1.blabla",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                "used_by": [],
            },
        )

    def test_used_by_unknown(self):
        self.assertResponse(
            "/v1/projects/backend/load-balancers/outputs/",
            {
                "hostname": {
                    "value": "https://hello.eu-central-1.blabla",
                    "deprecated": None,
                    "warning": None,
                    "sensitive": False,
                }
            },
            HTTP_X_watson_STACK="frontend/unknown",
        )
        self.assertResponse(
            "/v1/projects/backend/load-balancers/",
            {
                "id": "backend/load-balancers",
                "name": "Load-Balancers",
                "url": "http://testserver/v1/projects/backend/load-balancers/",
                "project": {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                },
                "outputs": {
                    "hostname": {
                        "value": "https://hello.eu-central-1.blabla",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    }
                },
                "used_by": [],
            },
        )

    @override_settings(WRAPPER="wrapper.ROT13Wrapper")
    def test_wrapped(self):
        response = self.client.post(
            "/v1/projects/backend/",
            {
                "name": "Wrapped",
                "outputs": {
                    "not_wrapped": {
                        "value": "test",
                    },
                    "wrapped": {
                        "value": "test",
                        "sensitive": True,
                    },
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertJSONEqual(
            response.content,
            {
                "id": "backend/wrapped",
                "name": "Wrapped",
                "outputs": {
                    "not_wrapped": {
                        "value": "test",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": False,
                    },
                    "wrapped": {
                        "value": "test",
                        "deprecated": None,
                        "warning": None,
                        "sensitive": True,
                    },
                },
                "url": "http://testserver/v1/projects/backend/wrapped/",
                "project": {
                    "id": "backend",
                    "name": "Backend",
                    "url": "http://testserver/v1/projects/backend/",
                },
                "used_by": [],
            },
        )
        self.assertEqual(
            Output.objects.values().get(key="not_wrapped"),
            {
                "deprecated": "",
                "id": 5,
                "key": "not_wrapped",
                "sensitive": False,
                "stack_id": 5,
                "value": "test",
                "warning": "",
            },
        )

        data = Output.objects.values().get(key="wrapped")
        value = data.pop("value")
        self.assertEqual(
            data,
            {
                "deprecated": "",
                "id": 6,
                "key": "wrapped",
                "sensitive": True,
                "stack_id": 5,
                "warning": "",
            },
        )
        self.assertNotEqual(value, "test")
