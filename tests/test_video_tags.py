import json
from unittest.mock import patch
import test_core as base
import test_editorial as editorial_base
from editorial import Editorial


def tags(markdown):
    return json.loads(next(line[6:] for line in markdown.splitlines() if line.startswith('tags: ')))


class VideoTagsTest(base.unittest.TestCase):
    setUp = base.CoreTest.setUp
    tearDown = base.CoreTest.tearDown
    capture = base.CoreTest.capture
    prepared = base.CoreTest.prepared

    def test_video_tag_is_in_draft_and_cannot_be_removed_before_save(self):
        c, proposal = self.prepared(kind='video')
        self.assertIn('video', proposal['draft']['tags'])
        self.assertEqual(tags(self.app.preview(c['id'], {'tags': []})['markdown']).count('video'), 1)
        saved = self.app.save(c['id'], {'tags': ['clases']})
        self.assertTrue({'clases', 'video'}.issubset(tags(base.Path(saved['path']).read_text())))

    def test_required_tag_does_not_displace_the_eight_existing_tags_or_duplicate_video(self):
        existing = ['tema-' + chr(97 + i) for i in range(8)]
        self.assertEqual(self.app.note_tags({'kind': 'video'}, existing), existing + ['video'])
        self.assertEqual(self.app.note_tags({'kind': 'video'}, ['VIDEO', '#video', 'clases']), ['video', 'clases'])
        self.assertEqual(self.app.note_tags({'kind': 'article'}, existing), existing)

    def test_vault_profile_cannot_remove_mandatory_video_tag(self):
        c, _ = self.prepared(kind='video')
        profile = self.app.vault_profile()
        for frontmatter, expected in [({}, ['video']), ({'tags': ['Curso/Nube', 'clase']}, ['Curso/Nube', 'clase', 'video'])]:
            with patch.object(self.app, 'vault_profile', return_value=profile), patch.object(profile, 'frontmatter', return_value=frontmatter):
                self.assertEqual(tags(self.app.preview(c['id'], {})['markdown']), expected)

    def test_all_derived_notes_keep_video_even_if_model_and_review_omit_it(self):
        c, result = editorial_base.EditorialTest.collection(self)
        stored = self.app.load(c['id']); stored['kind'] = 'video'; stored['media'] = {}; self.app.store(stored)
        result['source_format'] = 'video'
        for note in result['notes']:
            note['pages'] = []
        with patch.object(self.app, 'codex_generate', return_value=result):
            self.app.draft(c['id'], provider='codex', conversation='off')
        stored = self.app.load(c['id'])
        drafts = Editorial(self.app).drafts(stored)
        for draft in drafts.values():
            self.assertIn('video', draft['tags'])
        saved = self.app.save(c['id'], {'notes': {key: {'tags': []} for key in drafts}})
        self.assertEqual(saved['count'], 3)
        for path in saved['paths']:
            self.assertIn('video', tags((self.vault / path).read_text()))

    def test_old_pending_video_drafts_gain_tag_at_preview_without_regeneration(self):
        c, _ = self.prepared(kind='video')
        stored = self.app.load(c['id']); stored['draft']['tags'] = ['clase']; self.app.store(stored)
        self.assertTrue({'clase', 'video'}.issubset(tags(self.app.preview(c['id'], {})['markdown'])))

    def test_other_sources_do_not_get_video_automatically(self):
        c, proposal = self.prepared()
        self.assertNotIn('video', proposal['draft']['tags'])
        self.assertNotIn('video', tags(self.app.preview(c['id'], {})['markdown']))
