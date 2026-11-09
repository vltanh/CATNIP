"""Check the TreeSwift-based counter's degree convention and standalone CLI."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import treeswift


SCRIPT = Path(__file__).resolve().parents[1] / 'misc' / 'count_tob_blobs.py'
SPEC = importlib.util.spec_from_file_location('count_tob_blobs', SCRIPT)
COUNTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COUNTER)


class BlobCounterTests(unittest.TestCase):
    def summarize(self, text):
        return COUNTER.summarize(treeswift.read_tree_newick(text))

    def test_binary_trees_and_root_trifurcations_are_not_blobs(self):
        for tree in ['a;', '(a,b);', '(a,b,c);', '((a,b),(c,d));',
                     '(OUT,((a,b),(c,d)));', '((((a,b,c))));']:
            with self.subTest(tree=tree):
                self.assertEqual(self.summarize(tree)['blob_count'], 0)

    def test_root_and_nonroot_polytomies_include_correct_components(self):
        for tree, degrees, leaves in [
            ('(a,b,c,d);', [4], 4), ('(OUT,(a,b,c));', [4], 4),
            ('(OUT,(a,b,c,d));', [5], 5),
            ('((a,b,c),(d,e,f),g);', [4, 4], 7),
            ('(a,b,c,d,e,f);', [6], 6),
        ]:
            with self.subTest(tree=tree):
                self.assertEqual(self.summarize(tree), dict(
                    blob_count=len(degrees), blob_degrees=degrees, leaf_count=leaves))

    def test_rerooting_and_unary_root_chains_do_not_change_count(self):
        for tree in ['((a,b,c),(d,e,f),g);', '(a,(b,c,((d,e,f),g)));',
                     '(a,b,c,((d,e,f),g));', '((((a,b,c),(d,e,f),g)));']:
            with self.subTest(tree=tree):
                self.assertEqual(self.summarize(tree), dict(
                    blob_count=2, blob_degrees=[4, 4], leaf_count=7))

    def test_lengths_supports_and_quoted_labels_do_not_change_degree(self):
        text = "[&R] ('a,b':1e-3,'c d':-2,(e:0,f:1,g:2)95:.5)root:0;"
        self.assertEqual(self.summarize(text), dict(
            blob_count=1, blob_degrees=[4], leaf_count=5))

    def test_duplicate_missing_and_hybrid_labels_are_rejected(self):
        for tree in ['(a,a);', '(a,b,);', '(a,(b)#H1,#H1);']:
            with self.subTest(tree=tree):
                with self.assertRaises(ValueError):
                    self.summarize(tree)

    def test_copied_script_runs_without_catnip(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            script = directory / SCRIPT.name
            shutil.copyfile(SCRIPT, script)
            tree = directory / 'tree with spaces.nwk'
            tree.write_text('((a,b,c),(d,e,f),g);', encoding='utf-8')
            for options in [[], ['--json']]:
                process = subprocess.run([sys.executable, '-I', str(script), str(tree), *options],
                    capture_output=True, text=True, cwd=directory, timeout=10)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(process.stderr, '')
                if options:
                    self.assertEqual(json.loads(process.stdout), dict(
                        blob_count=2, blob_degrees=[4, 4], leaf_count=7))
                else:
                    self.assertEqual(process.stdout, '2\n')

    def test_cli_reports_installation_when_dependency_is_unavailable(self):
        process = subprocess.run([sys.executable, '-I', '-S', str(SCRIPT), 'unused.nwk'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(process.stdout, '')
        self.assertIn('python -m pip install treeswift==1.1.48', process.stderr)
        self.assertNotIn('Traceback', process.stderr)

    def test_cli_rejects_multiple_invalid_and_missing_files_without_a_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / 'input.nwk'
            for text in ['(a,b);\n(c,d);', '(a,b);(c,d);', '(a,b', '(a,a);',
                         '(a,(b)#H1,#H1);']:
                tree.write_text(text, encoding='utf-8')
                process = subprocess.run([sys.executable, '-I', str(SCRIPT), str(tree)],
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(process.returncode, 2, text)
                self.assertEqual(process.stdout, '')
                self.assertNotIn('Traceback', process.stderr)
            tree.unlink()
            process = subprocess.run([sys.executable, '-I', str(SCRIPT), str(tree)],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, '')


if __name__ == '__main__':
    unittest.main()
