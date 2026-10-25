"""Field of view under the rules' vision: symmetric shadowcasting (Albert Ford's) over a Chebyshev square, with
walls and other bush clusters opaque and invisible, and the viewer's own bush cluster transparent."""


def _scan(ox, oy, radius, quadrant, opaque, out):
    # Slopes are (num, den) with den > 0; rows are scanned at depth 1..radius.
    def tf(col, depth):
        if quadrant == 0:
            return ox + col, oy + depth
        if quadrant == 1:
            return ox + depth, oy + col
        if quadrant == 2:
            return ox + col, oy - depth
        return ox - depth, oy + col

    stack = [(1, -1, 1, 1, 1)]
    while stack:
        depth, sn, sd, en, ed = stack.pop()
        if depth > radius:
            continue
        # min_col = round_ties_up(depth * start), max_col = round_ties_down(depth * end)
        lo = (2 * depth * sn + sd) // (2 * sd)
        hi = -((ed - 2 * depth * en) // (2 * ed))
        prev = None
        for col in range(lo, hi + 1):
            x, y = tf(col, depth)
            wall = opaque(x, y)
            if wall or (col * sd >= depth * sn and col * ed <= depth * en):
                out.add((x, y))
            if prev is True and not wall:
                sn, sd = 2 * col - 1, 2 * depth
            if prev is False and wall:
                stack.append((depth + 1, sn, sd, 2 * col - 1, 2 * depth))
            prev = wall
        if prev is False:
            stack.append((depth + 1, sn, sd, en, ed))


class Vision:
    def __init__(self, W, H, walls, bush_cluster):
        self.W, self.H = W, H
        self.walls = walls
        self.bc = bush_cluster
        self.cache = {}

    def fov(self, p, radius=8):
        """Visible tiles from p (frozenset)."""
        key = (p, radius)
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        W, H, walls, bc = self.W, self.H, self.walls, self.bc
        own = bc.get(p)

        def opaque(x, y):
            if x < 0 or y < 0 or x >= W or y >= H or (x, y) in walls:
                return True
            c = bc.get((x, y))
            return c is not None and c != own

        seen = {p}
        for q in range(4):
            _scan(p[0], p[1], radius, q, opaque, seen)
        out = frozenset(t for t in seen if not opaque(*t))
        self.cache[key] = out
        return out
