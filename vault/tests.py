import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .audit import verify_chain
from .models import AuditLog, Document, Permission, User


class VaultTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ov = override_settings(PRIVATE_DIR=self.tmp)
        self.ov.enable()
        mk = lambda n, r: User.objects.create_user(n, password="x-Pass-12345", role=r)
        self.alice, self.bob = mk("alice", "owner"), mk("bob", "viewer")
        self.carol, self.adm = mk("carol", "viewer"), mk("adm", "admin")
        (self.tmp / "f1").write_bytes(b"top secret")
        self.doc = Document.objects.create(name="secret.txt", owner=self.alice, stored_name="f1", size=10)

    def tearDown(self):
        self.ov.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def client_for(self, user):
        c = Client()
        c.force_login(user)
        return c

    def url(self, name, *args):
        return reverse(name, args=[self.doc.id, *args])

    def test_anonymous_is_sent_to_login(self):
        r = Client().get(self.url("download"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_stranger_cannot_reach_document_on_any_route(self):
        c = self.client_for(self.bob)
        self.assertEqual(c.get(self.url("download")).status_code, 404)
        self.assertEqual(c.get(self.url("edit")).status_code, 404)
        self.assertEqual(c.post(self.url("edit"), {"name": "hacked"}).status_code, 404)
        self.assertEqual(c.post(self.url("delete")).status_code, 404)
        self.assertEqual(c.get(self.url("share")).status_code, 404)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.name, "secret.txt")
        self.assertFalse(self.doc.is_deleted)

    def test_owner_can_download(self):
        r = self.client_for(self.alice).get(self.url("download"))
        self.assertEqual(r.status_code, 200)
        r.close()

    def test_revoke_takes_effect_immediately(self):
        Permission.objects.create(document=self.doc, user=self.bob)
        c = self.client_for(self.bob)
        r = c.get(self.url("download"))
        self.assertEqual(r.status_code, 200)
        r.close()
        self.client_for(self.alice).post(self.url("revoke", self.bob.id))
        self.assertEqual(c.get(self.url("download")).status_code, 404)

    def test_read_only_cannot_edit_or_delete(self):
        Permission.objects.create(document=self.doc, user=self.bob, can_edit=False)
        c = self.client_for(self.bob)
        self.assertEqual(c.post(self.url("edit"), {"name": "x"}).status_code, 404)
        self.assertEqual(c.post(self.url("delete")).status_code, 404)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.name, "secret.txt")

    def test_edit_permission_allows_edit_but_not_delete(self):
        Permission.objects.create(document=self.doc, user=self.bob, can_edit=True)
        c = self.client_for(self.bob)
        c.post(self.url("edit"), {"name": "renamed.txt"})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.name, "renamed.txt")
        self.assertEqual(c.post(self.url("delete")).status_code, 404)

    def test_denied_attempt_is_audited(self):
        self.client_for(self.bob).get(self.url("download"))
        self.assertTrue(AuditLog.objects.filter(
            user_id=self.bob.id, action="download", result="denied", document_id=self.doc.id).exists())

    def test_search_does_not_leak_names(self):
        r = self.client_for(self.bob).get(reverse("index"), {"q": "secret"})
        self.assertNotContains(r, "secret.txt")

    def test_admin_has_no_content_access(self):
        c = self.client_for(self.adm)
        self.assertEqual(c.get(self.url("download")).status_code, 404)

    def test_non_owner_cannot_grant(self):
        self.client_for(self.bob).post(self.url("share"), {"username": "carol", "level": "read"})
        self.assertFalse(Permission.objects.filter(user=self.carol).exists())

    def test_viewer_cannot_upload(self):
        f = SimpleUploadedFile("a.txt", b"hello")
        r = self.client_for(self.bob).post(reverse("upload"), {"file": f})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Document.objects.count(), 1)

    def test_fake_pdf_rejected(self):
        f = SimpleUploadedFile("evil.pdf", b"this is not a pdf")
        self.client_for(self.alice).post(reverse("upload"), {"file": f})
        self.assertEqual(Document.objects.count(), 1)

    def test_audit_tampering_is_detected(self):
        self.client_for(self.bob).get(self.url("download"))
        self.assertIsNone(verify_chain())
        first = AuditLog.objects.order_by("id").first()
        AuditLog.objects.filter(pk=first.pk).update(result="allowed")
        self.assertIsNotNone(verify_chain())

    def test_audit_rows_cannot_be_modified(self):
        self.client_for(self.bob).get(self.url("download"))
        e = AuditLog.objects.first()
        e.result = "allowed"
        with self.assertRaises(PermissionError):
            e.save()

    def test_admin_is_sent_to_activity_page(self):
        r = self.client_for(self.adm).get(reverse("index"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("activity"))
