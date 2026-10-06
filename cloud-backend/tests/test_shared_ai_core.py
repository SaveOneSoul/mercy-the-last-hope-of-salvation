import unittest

from app.ai_ministry_policy import MinistryIdentity, can_access_ministry, private_menu
from app.shared_ai_core import AIIdentity, AICoreError, SharedAICore, authorize_ai_request


class FakeProvider:
    def generate(self, *, prompt, domain, context):
        return {"text": "raw provider response"}


class SharedCoreTest(unittest.TestCase):
    def setUp(self):
        self.owner = AIIdentity(
            subject="owner1", authenticated=True,
            domains=frozenset({"catholic"}), permissions=frozenset({"catholic:*"}),
        )

    def test_cross_domain_denied(self):
        with self.assertRaisesRegex(AICoreError, "domain_forbidden"):
            authorize_ai_request(self.owner, "insurance", "insurance:read")

    def test_provider_output_never_bypasses_validation(self):
        core = SharedAICore({"fake": FakeProvider()}, lambda **kwargs: {"approved": False})
        with self.assertRaisesRegex(AICoreError, "validation_failed"):
            core.execute(identity=self.owner, domain="catholic", permission="catholic:*",
                         provider="fake", prompt="hello")

    def test_approved_provider_output(self):
        core = SharedAICore({"fake": FakeProvider()},
                            lambda **kwargs: {"approved": True, "text": "reviewed", "sources": []})
        result = core.execute(identity=self.owner, domain="catholic", permission="catholic:*",
                              provider="fake", prompt="hello")
        self.assertEqual(result["text"], "reviewed")

    def test_private_menu_denied_to_customer(self):
        customer = MinistryIdentity("customer1", True, "web",
            frozenset({"insurance"}), frozenset({"advisor"}), frozenset())
        self.assertFalse(can_access_ministry(customer))
        self.assertEqual(private_menu(customer), [])

    def test_owner_requires_authenticated_web_session(self):
        owner = MinistryIdentity("owner1", True, "web", frozenset({"catholic"}),
                                 frozenset({"owner"}), frozenset())
        self.assertTrue(can_access_ministry(owner, "publish"))
        self.assertFalse(can_access_ministry(
            MinistryIdentity(owner.subject, True, "whatsapp", owner.domains,
                             owner.roles, owner.permissions)))

    def test_explicit_ministry_permission(self):
        member = MinistryIdentity("member1", True, "web", frozenset({"catholic"}),
                                  frozenset({"catechist"}), frozenset({"ministry:read"}))
        self.assertTrue(can_access_ministry(member))
        self.assertFalse(can_access_ministry(member, "publish"))


if __name__ == "__main__":
    unittest.main()
