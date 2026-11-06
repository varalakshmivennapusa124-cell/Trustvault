from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from .audit import log, verify_chain
from .models import AuditEntry, Document, Grant
from .permissions import can

User = get_user_model()
PW = "Test-pass-12345!"


class Base(TestCase):
    def setUp(self):
        mk = User.objects.create_user
        self.owner = mk("owner1", password=PW, role="owner")
        self.other = mk("owner2", password=PW, role="owner")
        self.viewer = mk("viewer1", password=PW, role="viewer")
        self.admin = mk("admin1", password=PW, role="admin")
        self.doc = Document.objects.create(
            owner=self.owner, name="secret.txt", category="hr",
            content_type="text/plain", size=6, data=b"SECRET",
        )
        self.dl = f"/documents/{self.doc.id}/download/"
        self.share = f"/documents/{self.doc.id}/share/"
        self.edit = f"/documents/{self.doc.id}/edit/"
        self.delete = f"/documents/{self.doc.id}/delete/"

    def as_user(self, user):
        c = Client()
        self.assertTrue(c.login(username=user.username, password=PW))
        return c

    def grant(self, user, level):
        Grant.objects.create(document=self.doc, user=user, level=level, granted_by=self.owner)


class CanTests(Base):
    def test_default_deny(self):
        for action in ("read", "edit", "delete", "share"):
            self.assertFalse(can(self.viewer, self.doc, action))
            self.assertFalse(can(self.admin, self.doc, action))

    def test_anonymous_and_inactive_denied(self):
        self.assertFalse(can(AnonymousUser(), self.doc, "read"))
        self.owner.is_active = False
        self.assertFalse(can(self.owner, self.doc, "read"))

    def test_owner_can_everything(self):
        for action in ("read", "edit", "delete", "share"):
            self.assertTrue(can(self.owner, self.doc, action))

    def test_read_grant_only_reads(self):
        self.grant(self.viewer, "read")
        self.assertTrue(can(self.viewer, self.doc, "read"))
        for action in ("edit", "delete", "share"):
            self.assertFalse(can(self.viewer, self.doc, action))

    def test_edit_grant_cannot_delete_or_share(self):
        self.grant(self.viewer, "edit")
        self.assertTrue(can(self.viewer, self.doc, "edit"))
        self.assertFalse(can(self.viewer, self.doc, "delete"))
        self.assertFalse(can(self.viewer, self.doc, "share"))


class AccessTests(Base):
    def test_anonymous_is_sent_to_login(self):
        r = Client().get(self.dl)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_owner_downloads(self):
        r = self.as_user(self.owner).get(self.dl)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"SECRET")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_other_owner_cannot_download(self):
        r = self.as_user(self.other).get(self.dl)
        self.assertEqual(r.status_code, 404)
        self.assertNotIn(b"SECRET", r.content)

    def test_viewer_without_grant_cannot_download(self):
        self.assertEqual(self.as_user(self.viewer).get(self.dl).status_code, 404)

    def test_admin_has_no_special_read_access(self):
        self.assertEqual(self.as_user(self.admin).get(self.dl).status_code, 404)

    def test_list_and_search_do_not_leak(self):
        c = self.as_user(self.other)
        self.assertNotContains(c.get("/"), "secret.txt")
        self.assertNotContains(c.get("/?q=secret"), "secret.txt")
        self.assertNotContains(c.get("/?category=hr&owner=owner1"), "secret.txt")

    def test_stranger_cannot_edit_delete_or_share(self):
        c = self.as_user(self.other)
        self.assertEqual(c.post(self.edit, {"name": "hacked", "category": "x"}).status_code, 404)
        self.assertEqual(c.post(self.delete).status_code, 404)
        self.assertEqual(
            c.post(self.share, {"action": "grant", "username": "owner2", "level": "edit"}).status_code, 404
        )
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.name, "secret.txt")
        self.assertTrue(Document.objects.filter(pk=self.doc.pk).exists())
        self.assertFalse(Grant.objects.exists())

    def test_read_grant_reads_but_cannot_change(self):
        self.grant(self.viewer, "read")
        c = self.as_user(self.viewer)
        self.assertEqual(c.get(self.dl).status_code, 200)
        self.assertEqual(c.post(self.edit, {"name": "x", "category": ""}).status_code, 404)
        self.assertEqual(c.post(self.delete).status_code, 404)

    def test_edit_grant_cannot_share_or_delete(self):
        self.grant(self.viewer, "edit")
        c = self.as_user(self.viewer)
        self.assertEqual(c.post(self.edit, {"name": "renamed.txt", "category": "hr"}).status_code, 302)
        self.assertEqual(c.post(self.delete).status_code, 404)
        self.assertEqual(
            c.post(self.share, {"action": "grant", "username": "owner2", "level": "read"}).status_code, 404
        )

    def test_delete_requires_post(self):
        self.assertEqual(self.as_user(self.owner).get(self.delete).status_code, 405)

    def test_revoke_takes_effect_immediately(self):
        owner_c, viewer_c = self.as_user(self.owner), self.as_user(self.viewer)
        owner_c.post(self.share, {"action": "grant", "username": "viewer1", "level": "read"})
        self.assertEqual(viewer_c.get(self.dl).status_code, 200)
        owner_c.post(self.share, {"action": "revoke", "username": "viewer1"})
        self.assertEqual(viewer_c.get(self.dl).status_code, 404)
        self.assertNotContains(viewer_c.get("/"), "secret.txt")

    def test_only_admin_sees_activity(self):
        self.assertEqual(self.as_user(self.owner).get("/activity/").status_code, 404)
        self.assertEqual(self.as_user(self.viewer).get("/activity/").status_code, 404)
        self.assertEqual(self.as_user(self.admin).get("/activity/").status_code, 200)


class UploadTests(Base):
    def test_upload_rules(self):
        c = self.as_user(self.owner)
        bad = SimpleUploadedFile("evil.exe", b"MZ", content_type="application/x-msdownload")
        c.post("/upload/", {"file": bad})
        self.assertFalse(Document.objects.filter(name="evil.exe").exists())
        big = SimpleUploadedFile("big.txt", b"x" * (5 * 1024 * 1024 + 1), content_type="text/plain")
        c.post("/upload/", {"file": big})
        self.assertFalse(Document.objects.filter(name="big.txt").exists())

    def test_viewer_cannot_upload(self):
        f = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
        r = self.as_user(self.viewer).post("/upload/", {"file": f})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Document.objects.filter(name="a.txt").exists())


class AuditTests(Base):
    def test_refused_attempts_are_recorded(self):
        self.as_user(self.other).get(self.dl)
        e = AuditEntry.objects.filter(action="download", outcome="denied").first()
        self.assertIsNotNone(e)
        self.assertEqual(e.actor_name, "owner2")

    def test_successful_actions_are_recorded(self):
        self.as_user(self.owner).get(self.dl)
        self.assertTrue(AuditEntry.objects.filter(action="download", outcome="allowed").exists())

    def test_chain_detects_edit(self):
        log(self.owner, "upload", self.doc)
        log(self.owner, "download", self.doc)
        self.assertTrue(verify_chain()[0])
        first = AuditEntry.objects.order_by("id").first()
        AuditEntry.objects.filter(pk=first.pk).update(actor_name="someone-else")
        ok, bad_id = verify_chain()
        self.assertFalse(ok)
        self.assertEqual(bad_id, first.pk)

    def test_chain_detects_removed_entry(self):
        for _ in range(3):
            log(self.owner, "download", self.doc)
        middle = AuditEntry.objects.order_by("id")[1]
        AuditEntry.objects.filter(pk=middle.pk).delete()
        self.assertFalse(verify_chain()[0])

    def test_entries_cannot_be_changed_or_deleted_via_model(self):
        e = log(self.owner, "upload", self.doc)
        e.detail = "x"
        with self.assertRaises(PermissionError):
            e.save()
        with self.assertRaises(PermissionError):
            e.delete()
