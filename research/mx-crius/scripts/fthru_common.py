"""Shared helpers for the fthru_* scripts."""


def bfs(W, H, block, srcs):
    INF = 10 ** 9
    dist = [INF] * (W * H)
    q = []
    for (x, y) in srcs:
        dist[y * W + x] = 0; q.append((x, y))
    h = 0
    while h < len(q):
        x, y = q[h]; h += 1
        d = dist[y * W + x] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (dx or dy) and 0 <= nx < W and 0 <= ny < H and not block[ny * W + nx] and dist[ny * W + nx] > d:
                    dist[ny * W + nx] = d; q.append((nx, ny))
    return dist
