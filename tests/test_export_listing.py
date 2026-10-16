import unittest

import kodistubs  # noqa: F401
from clouddrive.common.remote.provider import Provider


class TreeProvider(Provider):
    """list_subtree from a fixed tree; counts calls."""

    def __init__(self, tree, supports_subtree=True):
        super(TreeProvider, self).__init__('test')
        self.tree, self.supports_subtree = tree, supports_subtree
        self.subtree_calls, self.folder_calls = [], []

    def list_subtree(self, item_driveid, item_id):
        if not self.supports_subtree:
            return None
        self.subtree_calls.append(item_id)
        result, pending = {}, [item_id]
        while pending:
            folder = pending.pop()
            result[folder] = [dict(i) for i in self.tree.get(folder, [])]
            pending.extend(i['id'] for i in self.tree.get(folder, []) if 'folder' in i)
        return result

    def get_folder_items(self, item_driveid=None, item_id=None, path=None, on_items_page_completed=None, include_download_info=False, on_before_add_item=None):
        self.folder_calls.append((item_id, include_download_info))
        items = [dict(i) for i in self.tree.get(item_id, [])]
        for i in items:
            if on_before_add_item:
                on_before_add_item(i)
        return items


TREE = {'root': [{'id': 'A', 'folder': {}}, {'id': 'r'}], 'A': [{'id': 'a'}, {'id': 'B', 'folder': {}}], 'B': [{'id': 'b'}]}


class ExportListingTest(unittest.TestCase):
    def test_one_tree_listing_serves_every_folder_once(self):
        p = TreeProvider(TREE)
        seen = []
        hook = lambda item: seen.append(item['id'])
        self.assertEqual([i['id'] for i in p.get_export_folder_items('d', 'root', hook)], ['A', 'r'])
        self.assertEqual([i['id'] for i in p.get_export_folder_items('d', 'A', hook)], ['a', 'B'])
        self.assertEqual([i['id'] for i in p.get_export_folder_items('d', 'B', hook)], ['b'])
        self.assertEqual(p.subtree_calls, ['root'])
        self.assertEqual(seen, ['A', 'r', 'a', 'B', 'b'], 'the export hook runs on cached items too')
        p.get_export_folder_items('d', 'A')
        self.assertEqual(p.subtree_calls, ['root', 'A'], 'items are handed out once')

    def test_entries_expire(self):
        p = TreeProvider(TREE)
        p.get_export_folder_items('d', 'root')
        listed, items = p._subtree_cache['A']
        p._subtree_cache['A'] = (listed - Provider._SUBTREE_TTL - 1, items)
        p.get_export_folder_items('d', 'A')
        self.assertEqual(p.subtree_calls, ['root', 'A'])

    def test_services_without_a_tree_listing_list_each_folder(self):
        p = TreeProvider(TREE, supports_subtree=False)
        seen = []
        self.assertEqual([i['id'] for i in p.get_export_folder_items('d', 'A', lambda item: seen.append(item['id']))], ['a', 'B'])
        self.assertEqual(p.folder_calls, [('A', True)])
        self.assertEqual(seen, ['a', 'B'])

    def test_instances_do_not_share_the_cache(self):
        p, q = TreeProvider(TREE), TreeProvider(TREE)
        p.get_export_folder_items('d', 'root')
        self.assertNotIn('_subtree_cache', q.__dict__)
