#!/usr/bin/env python3
# Install the sole dependency: python -m pip install treeswift==1.1.48
"""Count unrooted degree >= 4 blob vertices in a TOB-QMC Newick file.

Run: python count_tob_blobs.py tree-of-blobs.nwk [--json]
This standalone script needs TreeSwift, but does not need CATNIP installed.
"""

import argparse
import json
from pathlib import Path


def summarize(tree):
    """Count multifurcations, including the parent edge for non-root nodes."""
    # Ignore unary root chains without changing the input tree.
    root = tree.root
    while root.num_children() == 1:
        root = root.child_nodes()[0]
    degrees = []
    labels = set()
    for node in root.traverse_preorder():
        if node.get_label() and '#' in node.get_label():
            raise ValueError('Expected an ordinary ToB tree, not extended Newick hybrid labels')
        if node.is_leaf():
            label = node.get_label()
            if not label or label in labels:
                raise ValueError('Leaf labels must be nonempty and unique')
            labels.add(label)
        degree = node.num_children() + int(node is not root)
        if degree >= 4:
            degrees.append(degree)
    return dict(blob_count=len(degrees), blob_degrees=sorted(degrees, reverse=True),
                leaf_count=len(labels))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tree', type=Path, help='One ordinary Newick tree from TOB-QMC')
    parser.add_argument('--json', action='store_true', help='Also report blob degrees and leaf count')
    args = parser.parse_args(argv)
    try:
        import treeswift
    except ImportError:
        parser.error('Install TreeSwift: python -m pip install treeswift==1.1.48')
    try:
        path = args.tree.resolve(strict=True)
        if not path.is_file():
            raise ValueError('Input must be a regular Newick file')
        # Pass the explicitly selected path to TreeSwift's file reader.
        tree = treeswift.read_tree_newick(str(path))
        if isinstance(tree, list):
            raise ValueError('Expected exactly one Newick tree')
        result = summarize(tree)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    except (RuntimeError, IndexError, AttributeError, RecursionError):
        # TreeSwift parse errors can include the entire input; keep errors brief.
        parser.error('Could not parse one complete Newick tree ending in a semicolon')
    print(json.dumps(result) if args.json else result['blob_count'])


if __name__ == '__main__':
    main()
