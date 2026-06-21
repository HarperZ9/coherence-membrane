"""graph_ops — pure stdlib operations over the Graph substrate.

No third-party imports. Every op is deterministic (fixed node/edge ordering from the
Graph substrate's normalisation) and total over a well-formed Graph; none mutate
their input. These are the re-derivation kernels the Graph criteria call to build
and re-check witnesses — kept separate from the criteria so a third party can re-run
a single op against a witness in isolation: adjacency, connected components, BFS
shortest-path + a cycle finder (the de Bruijn reachability kernel), de Bruijn
construction, serial transitive closure + tree jump-edges, and spanning/cut.
"""
from __future__ import annotations

from collections import deque
from itertools import product
from typing import Optional

from .graph import Edge, Graph, Node


def adjacency(g: Graph) -> dict[Node, tuple[Node, ...]]:
    """Out-adjacency map: node -> sorted out-neighbours, for EVERY declared node
    (isolated nodes map to ()). Deterministic; honours directedness via
    Graph.neighbors."""
    return {n: g.neighbors(n) for n in g.nodes}


def connected_components(g: Graph) -> tuple[tuple[Node, ...], ...]:
    """Weakly-connected components (edges traversed ignoring direction), each a
    sorted node tuple; the components themselves are returned in sorted order. A
    deterministic partition of the declared nodes — unknown edges do NOT connect
    anything (they are not real adjacency)."""
    # undirected reachability: build a symmetric adjacency over real edges only.
    adj: dict[Node, set[Node]] = {n: set() for n in g.nodes}
    for u, v in g.edges:
        adj[u].add(v)
        adj[v].add(u)
    seen: set[Node] = set()
    comps: list[tuple[Node, ...]] = []
    for start in g.nodes:  # g.nodes is already sorted -> deterministic component order
        if start in seen:
            continue
        stack = [start]
        comp: set[Node] = set()
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            seen.add(x)
            stack.extend(adj[x] - comp)
        comps.append(tuple(sorted(comp)))
    return tuple(sorted(comps))


def bfs_shortest_path(g: Graph, src, dst, *, max_nodes: Optional[int] = None) -> Optional[tuple[Node, ...]]:
    """A shortest (fewest-edges) path src..dst as a node tuple, or None if none / a
    bound was hit / an endpoint is undeclared. Deterministic: neighbours are visited
    in sorted order, so among equal-length paths the lexicographically smallest is
    returned. `max_nodes` caps how many nodes may be expanded (bounded search);
    returning None on the cap means "no decision within budget", never a false path.
    """
    from .graph import _norm_node

    s, t = _norm_node(src), _norm_node(dst)
    node_set = set(g.nodes)
    if s not in node_set or t not in node_set:
        return None
    if s == t:
        return (s,)
    adj = adjacency(g)
    prev: dict[Node, Node] = {s: s}
    q: deque[Node] = deque([s])
    expanded = 0
    while q:
        x = q.popleft()
        expanded += 1
        if max_nodes is not None and expanded > max_nodes:
            return None
        for nbr in adj[x]:  # already sorted
            if nbr in prev:
                continue
            prev[nbr] = x
            if nbr == t:
                # reconstruct
                path = [t]
                while path[-1] != s:
                    path.append(prev[path[-1]])
                return tuple(reversed(path))
            q.append(nbr)
    return None


def reaches(g: Graph, src, dst, *, max_nodes: Optional[int] = None) -> Optional[bool]:
    """True/False if `dst` is reachable from `src` within budget; None if a bound was
    hit (UNVERIFIABLE) or an endpoint is undeclared. False is a real closure result
    (the BFS exhausted reachable nodes without hitting the cap)."""
    from .graph import _norm_node

    s, t = _norm_node(src), _norm_node(dst)
    node_set = set(g.nodes)
    if s not in node_set or t not in node_set:
        return None
    if s == t:
        return True
    adj = adjacency(g)
    seen = {s}
    q: deque[Node] = deque([s])
    expanded = 0
    while q:
        x = q.popleft()
        expanded += 1
        if max_nodes is not None and expanded > max_nodes:
            return None  # budget exhausted -> no decision, never a false False
        for nbr in adj[x]:
            if nbr == t:
                return True
            if nbr not in seen:
                seen.add(nbr)
                q.append(nbr)
    return False


def find_cycle_through(g: Graph, label_node, *, max_nodes: Optional[int] = None) -> Optional[tuple[Node, ...]]:
    """A simple directed cycle passing through `label_node`, returned as a node tuple
    [label_node, ..., label_node] (first == last), or None if none exists / a bound
    was hit / the node is undeclared. The de Bruijn reachability kernel: a cycle
    through the labelled state witnesses the recurring-property claim. Deterministic
    (sorted neighbours -> the lexicographically-smallest shortest return path). None
    on the cap is UNVERIFIABLE, never a fabricated cycle."""
    from .graph import _norm_node

    n = _norm_node(label_node)
    if n not in set(g.nodes):
        return None
    adj = adjacency(g)
    # A cycle through n = an edge n->first, then a shortest path first..n not reusing
    # the closing edge. Search each out-neighbour deterministically.
    best: Optional[tuple[Node, ...]] = None
    for first in adj[n]:
        if first == n:  # a self-loop is the shortest cycle through n
            return (n, n)
        # shortest path first..n in the full graph (bounded)
        sub = bfs_shortest_path(g, first, n, max_nodes=max_nodes)
        if sub is None:
            continue
        cycle = (n,) + sub  # n -> first -> ... -> n
        if best is None or len(cycle) < len(best) or (len(cycle) == len(best) and cycle < best):
            best = cycle
    return best


# --- de Bruijn construction ---------------------------------------------------


def de_bruijn_graph(symbols, n: int) -> Graph:
    """The de Bruijn graph B(k, n): nodes are length-(n-1) words over `symbols`,
    a directed edge w -> w' iff w[1:] == w'[:-1] (overlap by n-1 chars). Used to turn
    a recurrence/transition claim over an alphabet into a reachability question (the
    'Prescribing the Death of a CA' construction). n>=1; n==1 yields the single empty
    node with a self-loop per symbol. Deterministic node/edge order via the Graph
    substrate. Symbols are coerced to single-char strings; raises ValueError on n<1.
    """
    if n < 1:
        raise ValueError("de Bruijn order n must be >= 1")
    syms = [str(s) for s in symbols]
    if not syms:
        raise ValueError("de Bruijn needs at least one symbol")
    k = n - 1
    nodes = ["".join(t) for t in product(syms, repeat=k)]  # length-(n-1) words
    edges: list[Edge] = [(w, (w + s)[1:] if k > 0 else "")  # overlap-by-(n-1) successor
                         for w in nodes for s in syms]
    return Graph(nodes=tuple(nodes), edges=tuple(edges), directed=True)


# --- serial transitive closure (composable jump-edges) ------------------------


def transitive_closure(g: Graph, *, max_nodes: Optional[int] = None) -> Optional[frozenset[tuple[Node, Node]]]:
    """Serial transitive closure: the set of all (a, b) with b reachable from a
    (a != b), honouring directedness. Returns None if the graph exceeds `max_nodes`
    (the closure is O(V*(V+E)); past the cap it is UNVERIFIABLE-in-practice, not
    silently truncated). This is the precompute behind composable reachability
    certificates: any reachability fact is then ONE membership test. Deterministic
    (the result is a set; iteration order is irrelevant to membership)."""
    if max_nodes is not None and g.node_count() > max_nodes:
        return None
    adj = adjacency(g)
    closure: set[tuple[Node, Node]] = set()
    for s in g.nodes:
        # BFS from s over real edges
        seen = {s}
        q: deque[Node] = deque([s])
        while q:
            x = q.popleft()
            for nbr in adj[x]:
                if nbr not in seen:
                    seen.add(nbr)
                    q.append(nbr)
        for b in seen:
            if b != s:
                closure.add((s, b))
    return frozenset(closure)


def tree_jump_edges(g: Graph, root, *, max_nodes: Optional[int] = None) -> Optional[dict[Node, tuple[Node, ...]]]:
    """For a tree rooted at `root` (directed away from root, or undirected acyclic),
    the ancestor chain of every node: node -> (root..parent) in root-first order. The
    'serial transitive closure on a tree' precompute — a node's reachability-from is
    EXACTLY its ancestor set, so any reachability certificate is one composition of
    these jump-edges. Returns None over the cap, or None if the structure is not a
    tree reachable from root (a cycle / unreached node makes the ancestor chain
    ill-defined -> UNVERIFIABLE, never a wrong chain)."""
    from .graph import _norm_node

    r = _norm_node(root)
    if r not in set(g.nodes):
        return None
    if max_nodes is not None and g.node_count() > max_nodes:
        return None
    adj = adjacency(g)
    parent: dict[Node, Node] = {r: r}
    order: list[Node] = [r]
    q: deque[Node] = deque([r])
    while q:
        x = q.popleft()
        for nbr in adj[x]:
            if nbr in parent:
                if parent[x] == nbr or nbr == r:
                    continue
                # nbr already has a parent and it's not x's link back -> not a tree
                return None
            parent[nbr] = x
            order.append(nbr)
            q.append(nbr)
    if len(parent) != g.node_count():
        return None  # some node unreachable from root -> ancestor chain ill-defined
    chains: dict[Node, tuple[Node, ...]] = {}
    for node in order:
        chain: list[Node] = []
        cur = node
        while cur != r:
            cur = parent[cur]
            chain.append(cur)
        chains[node] = tuple(reversed(chain))  # root-first ancestors (excludes node)
    return chains


# --- spanning + cut (the bottleneck-certificate kernels) ----------------------


def spans(nodes: tuple[Node, ...], edges) -> Optional[dict]:
    """Union-find: return the parent map iff `edges` connect ALL `nodes` into one
    component, else None. O(E * inverse-Ackermann). Edges naming a node outside
    `nodes` are skipped (they cannot connect declared nodes). The re-check kernel for
    a bottleneck certificate's spanning + minimality (cut) conditions."""
    parent = {n: n for n in nodes}

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression
            parent[x], x = root, parent[x]
        return root

    for u, v in edges:
        if u not in parent or v not in parent:
            continue
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    if not nodes:
        return None
    roots = {find(n) for n in nodes}
    return parent if len(roots) == 1 else None


def connects_all(nodes: tuple[Node, ...], edges) -> bool:
    """A SECOND, independent connectivity decider: True iff `edges` connect ALL `nodes`
    into one component, by BFS-reachability over the edge set — DISJOINT from the
    union-find `spans()` (no shared helper, no shared kernel). Edges naming a node
    outside `nodes` are skipped (they cannot connect declared nodes); empty `nodes` is
    False (no single component to span).

    Why a duplicate of `spans()`'s connectivity question on a different algorithm: the
    bottleneck certificate's load-bearing connectivity checks (is the claim spanning?
    do sub-bottleneck edges disconnect?) must not both flow through ONE kernel, or a
    bug in that kernel is a latent false VERIFIED the re-checker cannot see. Two
    algorithms that AGREE shrink the trusted base to 'they are not both wrong the same
    way' (cf. crosscheck.py); a disagreement is a caught bug (UNVERIFIABLE), never a
    guess. Builds its own adjacency inline on purpose so it shares NO code path with
    union-find. Deterministic; never mutates input."""
    if not nodes:
        return False
    # own adjacency over real edges only — built here, NOT via adjacency()/cut_sides,
    # so this decider is genuinely disjoint from every other connectivity helper.
    adj: dict[Node, set[Node]] = {n: set() for n in nodes}
    node_set = set(nodes)
    for u, v in edges:
        if u in node_set and v in node_set:
            adj[u].add(v)
            adj[v].add(u)  # connectivity is undirected (same notion spans() decides)
    start = nodes[0]
    seen: set[Node] = {start}
    q: deque[Node] = deque([start])
    while q:
        x = q.popleft()
        for nbr in adj[x]:
            if nbr not in seen:
                seen.add(nbr)
                q.append(nbr)
    return len(seen) == len(node_set)


def cut_sides(nodes: tuple[Node, ...], edges) -> tuple[set, set]:
    """Partition `nodes` into the component containing the smallest node (under
    `edges`) and the rest — the cut a sub-bottleneck edge set fails to bridge, carried
    as a bottleneck-minimality witness. Deterministic (nodes are sorted)."""
    adj: dict[Node, set] = {n: set() for n in nodes}
    for u, v in edges:
        if u in adj and v in adj:
            adj[u].add(v)
            adj[v].add(u)
    start = nodes[0]
    seen = {start}
    stack = [start]
    while stack:
        x = stack.pop()
        for nbr in adj[x]:
            if nbr not in seen:
                seen.add(nbr)
                stack.append(nbr)
    return seen, set(nodes) - seen
