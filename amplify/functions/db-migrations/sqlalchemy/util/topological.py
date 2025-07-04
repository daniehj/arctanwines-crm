# util/topological.py
# Copyright (C) 2005-2023 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""Topological sorting algorithms."""

from .. import util
from ..exc import CircularDependencyError

__all__ = ["sort", "sort_as_subsets", "find_cycles"]


def sort_as_subsets(tuples, allitems):
    edges = util.defaultdict(set)
    for parent, child in tuples:
        edges[child].add(parent)

    todo = list(allitems)
    todo_set = set(allitems)

    while todo_set:
        output = []
        for node in todo:
            if todo_set.isdisjoint(edges[node]):
                output.append(node)

        if not output:
            raise CircularDependencyError(
                "Circular dependency detected.",
                find_cycles(tuples, allitems),
                _gen_edges(edges),
            )

        todo_set.difference_update(output)
        todo = [t for t in todo if t in todo_set]
        yield output


def sort(tuples, allitems, deterministic_order=True):
    """sort the given list of items by dependency.

    'tuples' is a list of tuples representing a partial ordering.

    deterministic_order is no longer used, the order is now always
    deterministic given the order of "allitems".    the flag is there
    for backwards compatibility with Alembic.

    """

    for set_ in sort_as_subsets(tuples, allitems):
        for s in set_:
            yield s


def find_cycles(tuples, allitems):
    # adapted from:
    # https://neopythonic.blogspot.com/2009/01/detecting-cycles-in-directed-graph.html

    edges = util.defaultdict(set)
    for parent, child in tuples:
        edges[parent].add(child)
    nodes_to_test = set(edges)

    output = set()

    # we'd like to find all nodes that are
    # involved in cycles, so we do the full
    # pass through the whole thing for each
    # node in the original list.

    # we can go just through parent edge nodes.
    # if a node is only a child and never a parent,
    # by definition it can't be part of a cycle.  same
    # if it's not in the edges at all.
    for node in nodes_to_test:
        stack = [node]
        todo = nodes_to_test.difference(stack)
        while stack:
            top = stack[-1]
            for node in edges[top]:
                if node in stack:
                    cyc = stack[stack.index(node) :]
                    todo.difference_update(cyc)
                    output.update(cyc)

                if node in todo:
                    stack.append(node)
                    todo.remove(node)
                    break
            else:
                node = stack.pop()
    return output


def _gen_edges(edges):
    return set([(right, left) for left in edges for right in edges[left]])
