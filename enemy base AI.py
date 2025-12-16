import pygame
import random
import math
from math import hypot
import heapq

# -------------------- CONFIGURATION --------------------
SCREEN_W, SCREEN_H = 500, 500
TILE = 32                 # tile size used for walls and pathfinding
FPS = 60

# -------------------- A STAR PATHFINDING --------------------
def astar(start, goal, blocked, grid_w, grid_h):
    """
    A* search on a 4-connected grid.
    - start, goal: (tx, ty) tile coordinates
    - blocked: set of blocked tile coords
    Returns a list of tile coords from start (excluded) to goal (included).
    """
    if start == goal:
        return []

    def h(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan heuristic

    open_heap = []
    heapq.heappush(open_heap, (h(start, goal), 0, start, None))
    came_from = {}
    gscore = {start: 0}
    closed = set()

    while open_heap:
        f, g, current, parent = heapq.heappop(open_heap)
        if current in closed:
            continue
        came_from[current] = parent

        if current == goal:
            # reconstruct path from start to goal (excluding start)
            path = []
            node = current
            while node != start:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path

        closed.add(current)

        cx, cy = current
        neighbors = [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]
        for n in neighbors:
            nx, ny = n
            if nx < 0 or ny < 0 or nx >= grid_w or ny >= grid_h:
                continue
            if n in blocked:
                continue
            tentative_g = g + 1
            if tentative_g < gscore.get(n, 1e9):
                gscore[n] = tentative_g
                heapq.heappush(open_heap, (tentative_g + h(n, goal), tentative_g, n, current))

    return []  # no path found

# -------------------- ENEMY SPRITE WITH PATHFINDING --------------------
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, speed, hp=3, size=20):
        super().__init__()
        self.image = pygame.Surface([size, size])
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect()

        # Use float positions for smooth movement
        self.x = float(x)
        self.y = float(y)
        self.rect.center = (int(self.x), int(self.y))

        # movement and combat state
        self.speed = speed
        self.hp = hp
        self.invul = 0           # invulnerability frames after hit
        self.kb_vx = 0.0         # knockback velocity x
        self.kb_vy = 0.0         # knockback velocity y

        # pathfinding state
        self.path = []           # list of tile coords to follow
        self.path_index = 0      # next node index in path
        self.path_cooldown = 0   # frames until next path calc allowed
        self.last_player_tile = None

    def update(self):
        """Update visual state and apply knockback decay each frame."""
        if self.invul > 0:
            self.invul -= 1
            self.image.fill((200, 120, 120))  # flash color when invulnerable
        else:
            self.image.fill((0, 255, 0))

        # apply knockback and decay it
        if abs(self.kb_vx) > 0.01 or abs(self.kb_vy) > 0.01:
            self.x += self.kb_vx
            self.y += self.kb_vy
            self.kb_vx *= 0.8
            self.kb_vy *= 0.8

        # sync rect with float position
        self.rect.center = (int(self.x), int(self.y))

    def move_along_path(self):
        """
        Move toward the next path node (tile center).
        If path is exhausted, do nothing here (fallback chase handled externally).
        """
        if self.path_index >= len(self.path):
            return

        tx, ty = self.path[self.path_index]
        target_x = tx * TILE + TILE // 2
        target_y = ty * TILE + TILE // 2

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            self.path_index += 1
            return

        move_dist = min(self.speed, dist)
        self.x += (dx / dist) * move_dist
        self.y += (dy / dist) * move_dist
        self.rect.center = (int(self.x), int(self.y))

        # advance to next node when close enough
        if dist < 4:
            self.path_index += 1

    def request_path(self, player_rect, blocked_tiles, grid_w, grid_h):
        """
        Recalculate path to the player's tile when needed.
        - Throttled by path_cooldown to avoid heavy CPU usage.
        - If start or goal tile is blocked, try nearby free tiles.
        """
        if self.path_cooldown > 0:
            return

        my_tile = (int(self.x) // TILE, int(self.y) // TILE)
        player_tile = (player_rect.centerx // TILE, player_rect.centery // TILE)

        # skip recalculation if player tile unchanged and we already have a path
        if self.last_player_tile == player_tile and self.path:
            return

        self.last_player_tile = player_tile

        # if start tile blocked, try to find a nearby free tile
        if my_tile in blocked_tiles:
            found = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cand = (my_tile[0] + dx, my_tile[1] + dy)
                    if 0 <= cand[0] < grid_w and 0 <= cand[1] < grid_h and cand not in blocked_tiles:
                        my_tile = cand
                        found = True
                        break
                if found:
                    break
            if not found:
                return

        # if player tile blocked, try adjacent free tile
        if player_tile in blocked_tiles:
            found = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cand = (player_tile[0] + dx, player_tile[1] + dy)
                    if 0 <= cand[0] < grid_w and 0 <= cand[1] < grid_h and cand not in blocked_tiles:
                        player_tile = cand
                        found = True
                        break
                if found:
                    break
            if not found:
                return

        # compute path and reset index
        path = astar(my_tile, player_tile, blocked_tiles, grid_w, grid_h)
        self.path = path
        self.path_index = 0
        self.path_cooldown = 12  # small cooldown in frames

    def tick_path_cooldown(self):
        """Decrease path cooldown each frame."""
        if self.path_cooldown > 0:
            self.path_cooldown -= 1

    def take_damage(self, amount, kb_x=0.0, kb_y=0.0, invul_frames=12):
        """Apply damage, set knockback and invulnerability. Return True if dead."""
        if self.invul > 0:
            return False
        self.hp -= amount
        self.invul = invul_frames
        self.kb_vx += kb_x
        self.kb_vy += kb_y
        return self.hp <= 0

# -------------------- MAIN GAME --------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    # colors used in drawing
    PURP = (250, 0, 250)   # walls
    RED  = (250, 0, 0)     # sword hitbox debug
    YELL = (250, 250, 0)   # player
    GREY = (80, 80, 80)    # UI background

    # helper: axis-separated movement with collision resolution
    def move_player(player, walls, px, py, dx, dy):
        px += dx
        player.x = int(px)
        if player.collidelist(walls) != -1:
            px -= dx
            player.x = int(px)

        py += dy
        player.y = int(py)
        if player.collidelist(walls) != -1:
            py -= dy
            player.y = int(py)

        return px, py

    # helper: compute an axis-aligned sword rect in front of player
    def get_mouse_sword_hitbox(player, dir_x, dir_y, angle_offset=0):
        reach = 28
        length = 24
        thickness = 12
        angle = math.atan2(dir_y, dir_x) + angle_offset
        cx = player.centerx + math.cos(angle) * reach
        cy = player.centery + math.sin(angle) * reach
        if abs(math.cos(angle)) > abs(math.sin(angle)):
            return pygame.Rect(cx - length // 2, cy - thickness // 2, length, thickness)
        else:
            return pygame.Rect(cx - thickness // 2, cy - length // 2, thickness, length)

    # player setup
    player = pygame.Rect(100, 100, 24, 24)
    px, py = float(player.x), float(player.y)

    # generate dungeon walls, skipping the player's starting tile
    walls = []
    for y in range(25):
        for x in range(25):
            if random.random() < 0.3:
                rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
                if rect.colliderect(player):
                    continue
                walls.append(rect)

    # build blocked tile set for pathfinding from walls
    grid_w = SCREEN_W // TILE
    grid_h = SCREEN_H // TILE
    blocked_tiles = set()
    for w in walls:
        tx = w.x // TILE
        ty = w.y // TILE
        blocked_tiles.add((tx, ty))

    # spawn enemies as sprites, avoiding walls and player
    enemies = pygame.sprite.Group()
    spawn_attempts = 0
    while len(enemies) < 8 and spawn_attempts < 500:
        spawn_attempts += 1
        ex = random.randint(0, SCREEN_W - 20)
        ey = random.randint(0, SCREEN_H - 20)
        r = pygame.Rect(ex, ey, 20, 20)
        if r.collidelist(walls) == -1 and not r.colliderect(player):
            spd = random.uniform(0.6, 1.6)
            e = Enemy(ex, ey, spd, hp=2, size=20)
            enemies.add(e)

    # gameplay variables
    speed = 2
    run = True

    # attack state
    attacking = False
    attack_timer = 0
    ATTACK_DURATION = 8
    ARC_ANGLE = math.pi / 6  # swing arc

    # cooldown and combat values
    COOLDOWN = 12
    cooldown_timer = 0
    DAMAGE_PER_HIT = 1
    KNOCKBACK_STRENGTH = 6.0

    # track player's tile to trigger path recalculation when they move tiles
    player_tile = (player.centerx // TILE, player.centery // TILE)

    # -------------------- MAIN LOOP --------------------
    while run:
        clock.tick(FPS)
        screen.fill((0, 0, 0))

        # input and movement
        dx = dy = 0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            dx -= speed
        if keys[pygame.K_d]:
            dx += speed
        if keys[pygame.K_z]:
            dy -= speed
        if keys[pygame.K_s]:
            dy += speed

        px, py = move_player(player, walls, px, py, dx, dy)

        # detect if player moved to a different tile
        new_player_tile = (player.centerx // TILE, player.centery // TILE)
        player_moved_tile = new_player_tile != player_tile
        player_tile = new_player_tile

        # update enemies: path requests, movement, and state updates
        for e in list(enemies):
            e.tick_path_cooldown()

            # request a new path if player moved tile or cooldown expired
            if player_moved_tile or e.path_cooldown == 0:
                e.request_path(player, blocked_tiles, grid_w, grid_h)

            # follow path if available, otherwise fallback to direct chase
            if e.path:
                e.move_along_path()
            else:
                # fallback direct chase (keeps behavior if no path found)
                dx_e = player.centerx - e.x
                dy_e = player.centery - e.y
                dist = math.hypot(dx_e, dy_e)
                if dist != 0:
                    e.x += (dx_e / dist) * e.speed
                    e.y += (dy_e / dist) * e.speed
                    e.rect.center = (int(e.x), int(e.y))

            # apply invul/knockback visuals and movement
            e.update()

            # clamp inside screen and sync float pos
            e.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_W, SCREEN_H))
            e.x, e.y = float(e.rect.centerx), float(e.rect.centery)

        # sword attack logic
        sword_hitbox = None
        if attacking:
            mx, my = pygame.mouse.get_pos()
            dir_x = mx - player.centerx
            dir_y = my - player.centery
            length_dir = math.hypot(dir_x, dir_y)
            if length_dir != 0:
                dir_x /= length_dir
                dir_y /= length_dir

            t = (ATTACK_DURATION - attack_timer) / ATTACK_DURATION
            angle_offset = (t - 0.5) * ARC_ANGLE
            sword_hitbox = get_mouse_sword_hitbox(player, dir_x, dir_y, angle_offset)

            # cancel hitbox if it intersects a wall (sword blocked)
            if sword_hitbox and sword_hitbox.collidelist(walls) != -1:
                sword_hitbox = None

            # apply damage and knockback to enemies hit
            if sword_hitbox:
                for e in list(enemies):
                    if sword_hitbox.colliderect(e.rect):
                        kb_dx = e.rect.centerx - player.centerx
                        kb_dy = e.rect.centery - player.centery
                        kb_len = math.hypot(kb_dx, kb_dy)
                        if kb_len == 0:
                            kb_dx, kb_dy = 0.0, -1.0
                            kb_len = 1.0
                        kb_dx /= kb_len
                        kb_dy /= kb_len

                        died = e.take_damage(
                            DAMAGE_PER_HIT,
                            kb_x=kb_dx * KNOCKBACK_STRENGTH,
                            kb_y=kb_dy * KNOCKBACK_STRENGTH,
                            invul_frames=12
                        )
                        if died:
                            enemies.remove(e)

            attack_timer -= 1
            if attack_timer <= 0:
                attacking = False
                cooldown_timer = COOLDOWN

        # cooldown tick
        if cooldown_timer > 0:
            cooldown_timer -= 1

        # -------------------- DRAW --------------------
        # player
        pygame.draw.rect(screen, YELL, player)

        # walls
        for wall in walls:
            pygame.draw.rect(screen, PURP, wall)

        # enemies
        enemies.draw(screen)

        # debug: draw remaining path nodes for each enemy (optional)
        for e in enemies:
            if e.path:
                for node in e.path[e.path_index:]:
                    cx = node[0] * TILE + TILE // 2
                    cy = node[1] * TILE + TILE // 2
                    pygame.draw.circle(screen, (100, 200, 255), (cx, cy), 3)

        # sword hitbox debug
        if sword_hitbox:
            pygame.draw.rect(screen, RED, sword_hitbox)

        # cooldown bar above player
        bar_w, bar_h = 40, 6
        bar_x = player.centerx - bar_w // 2
        bar_y = player.top - 12
        pygame.draw.rect(screen, GREY, (bar_x, bar_y, bar_w, bar_h))
        if cooldown_timer > 0:
            frac = cooldown_timer / COOLDOWN
            pygame.draw.rect(screen, (200, 50, 50), (bar_x, bar_y, int(bar_w * (1 - frac)), bar_h))
        else:
            pygame.draw.rect(screen, (50, 200, 50), (bar_x, bar_y, bar_w, bar_h))

        # -------------------- EVENTS --------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not attacking and cooldown_timer == 0:
                    attacking = True
                    attack_timer = ATTACK_DURATION

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()