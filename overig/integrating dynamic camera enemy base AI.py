# Integrated dynamic camera into enemy base AI
# File: enemy_base_AI_camera.py

import pygame
import random
import math
from math import hypot
import heapq

# ---------------------- CONFIGURATION ----------------------
SCREEN_W, SCREEN_H = 500, 500  # window size
WORLD_W, WORLD_H = 2000, 2000  # world size (scrollable)
TILE = 32                      # tile size used for walls and pathfinding
FPS = 60

# ---------------------- CAMERA -----------------------------
class Camera:
    """Simple camera that centers on a target and provides an offset for drawing."""
    def __init__(self, screen_w, screen_h, world_w, world_h):
        self.offset = pygame.math.Vector2(0, 0)
        self.half_w = screen_w // 2
        self.half_h = screen_h // 2
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.world_w = world_w
        self.world_h = world_h

    def center_on(self, target_rect):
        self.offset.x = target_rect.centerx - self.half_w
        self.offset.y = target_rect.centery - self.half_h
        # Clamp camera to world bounds so you can't see outside
        self.offset.x = max(0, min(self.offset.x, self.world_w - self.screen_w))
        self.offset.y = max(0, min(self.offset.y, self.world_h - self.screen_h))

    def to_world(self, screen_pos):
        """Convert a point from screen coordinates to world coordinates."""
        return (screen_pos[0] + int(self.offset.x), screen_pos[1] + int(self.offset.y))

    def blit_group(self, surface, group):
        """Draw sprites in a group with camera offset (sorted by y for simple layering)."""
        for sprite in sorted(group.sprites(), key=lambda s: s.rect.centery):
            surface.blit(sprite.image, (sprite.rect.x - self.offset.x,
                                        sprite.rect.y - self.offset.y))

    def blit_surface(self, surface, img, rect):
        surface.blit(img, (rect.x - self.offset.x, rect.y - self.offset.y))

# ---------------------- UTILITIES --------------------------
# Helper functie: compute an axis-aligned sword rect in front of player
# (Kept from the original basic AI code)
def get_mouse_sword_hitbox(player_rect, dir_x, dir_y, angle_offset=0):
    reach = 28
    length = 24
    thickness = 12
    angle = math.atan2(dir_y, dir_x) + angle_offset
    cx = player_rect.centerx + math.cos(angle) * reach
    cy = player_rect.centery + math.sin(angle) * reach
    if abs(math.cos(angle)) > abs(math.sin(angle)):
        return pygame.Rect(cx - length // 2, cy - thickness // 2, length, thickness)
    else:
        return pygame.Rect(cx - thickness // 2, cy - length // 2, thickness, length)

# Quick helper to check collision of an arbitrary rect against any wall sprite
# This avoids creating temporary Wall sprites each time

def rect_collides_walls(rect, walls_group):
    for w in walls_group:
        if rect.colliderect(w.rect):
            return True
    return False

# ---------------------- A STAR PATHFINDING -----------------

def astar(start, goal, blocked, grid_w, grid_h):
    if start == goal:
        return []

    def h(a, b):
        x_squared = (a[0] - b[0])**2
        y_squared = (a[1] - b[1])**2
        return math.sqrt(x_squared + y_squared)  # Euclidean heuristic

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
        # 4-neighborhood (no diagonals)
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

# ---------------------- SPRITES ----------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, size=24, speed=2, max_hp=10, cooldown=4):
        super().__init__()
        self.size = size
        self.image = pygame.Surface([size, size])
        self.image.fill((250, 250, 0))  # yellow
        self.rect = self.image.get_rect(topleft=(x, y))
        # float pos for smooth movement
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        # health
        self.max_hp = max_hp
        self.hp = max_hp
        # combat state
        self.cooldown_timer = 0
        self.COOLDOWN = cooldown
        self.is_attacking = False

    def handle_input(self):
        """Lees toetsenbordinput (Q/D/Z/S) en bereken gewenste beweging."""
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_q]:
            dx -= self.speed
        if keys[pygame.K_d]:
            dx += self.speed
        if keys[pygame.K_z]:
            dy -= self.speed
        if keys[pygame.K_s]:
            dy += self.speed
        return dx, dy

    def move(self, dx, dy, walls):
        """Pas beweging toe en los botsingen op met muren (axis-aligned)."""
        # X-axis movement
        self.x += dx
        self.rect.topleft = (int(self.x), int(self.y))
        if pygame.sprite.spritecollideany(self, walls):
            self.x -= dx  # revert
            self.rect.topleft = (int(self.x), int(self.y))
        # Y-axis movement
        self.y += dy
        self.rect.topleft = (int(self.x), int(self.y))
        if pygame.sprite.spritecollideany(self, walls):
            self.y -= dy  # revert
            self.rect.topleft = (int(self.x), int(self.y))

    def update(self, walls):
        # 1. Cooldown tick
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        # 2. Movement
        dx, dy = self.handle_input()
        self.move(dx, dy, walls)
        # 3. Clamp inside WORLD
        self.rect.clamp_ip(pygame.Rect(0, 0, WORLD_W, WORLD_H))
        self.x, self.y = float(self.rect.left), float(self.rect.top)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        print("Speler is verslagen!")
        self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, speed, hp=3, size=20):
        super().__init__()
        self.image = pygame.Surface([size, size])
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect()
        self.x = float(x)
        self.y = float(y)
        self.rect.center = (int(self.x), int(self.y))
        self.speed = speed
        self.hp = hp
        self.invul = 0
        self.kb_vx = 0.0
        self.kb_vy = 0.0
        self.path = []
        self.path_index = 0
        self.path_cooldown = 0
        self.last_player_tile = None

    def update(self, walls):
        # flash color when invulnerable
        if self.invul > 0:
            self.invul -= 1
            self.image.fill((200, 120, 120))
        else:
            self.image.fill((0, 255, 0))
        # apply knockback and decay it
        if abs(self.kb_vx) > 0.01 or abs(self.kb_vy) > 0.01:
            self.x += self.kb_vx
            self.y += self.kb_vy
            self.rect.center = (int(self.x), int(self.y))
            if pygame.sprite.spritecollideany(self, walls):  # collided, revert
                self.x -= self.kb_vx
                self.y -= self.kb_vy
                self.rect.center = (int(self.x), int(self.y))
                self.kb_vx = 0
                self.kb_vy = 0
            self.kb_vx *= 0.8
            self.kb_vy *= 0.8
        # sync & clamp to world
        self.rect.center = (int(self.x), int(self.y))
        self.rect.clamp_ip(pygame.Rect(0, 0, WORLD_W, WORLD_H))
        self.x, self.y = float(self.rect.centerx), float(self.rect.centery)

    def move_along_path(self):
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
        if dist < 4:
            self.path_index += 1

    def request_path(self, player_rect, blocked_tiles, grid_w, grid_h):
        if self.path_cooldown > 0:
            return
        my_tile = (int(self.x) // TILE, int(self.y) // TILE)
        player_tile = (player_rect.centerx // TILE, player_rect.centery // TILE)
        if self.last_player_tile == player_tile and self.path:
            return
        self.last_player_tile = player_tile
        # ensure start and goal tiles are free or find nearby
        def find_near_free(tile):
            if tile not in blocked_tiles:
                return tile
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cand = (tile[0] + dx, tile[1] + dy)
                    if 0 <= cand[0] < grid_w and 0 <= cand[1] < grid_h and cand not in blocked_tiles:
                        return cand
            return None
        my_tile = find_near_free(my_tile)
        player_tile = find_near_free(player_tile)
        if my_tile is None or player_tile is None:
            return
        path = astar(my_tile, player_tile, blocked_tiles, grid_w, grid_h)
        self.path = path
        self.path_index = 0
        self.path_cooldown = 12

    def tick_path_cooldown(self):
        if self.path_cooldown > 0:
            self.path_cooldown -= 1

    def take_damage(self, amount, kb_x=0.0, kb_y=0.0, invul_frames=12):
        if self.invul > 0:
            return False
        self.hp -= amount
        self.invul = invul_frames
        self.kb_vx += kb_x
        self.kb_vy += kb_y
        return self.hp <= 0

class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = TILE
        self.image = pygame.Surface([size, size])
        self.image.fill((250, 0, 250))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

# ---------------------- MAIN GAME --------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    # colors used in drawing
    RED = (250, 0, 0)
    GREY = (80, 80, 80)

    # player setup
    player_size = 24
    start_x, start_y = 100, 100
    player = Player(start_x, start_y, size=player_size)
    player_group = pygame.sprite.GroupSingle(player)

    # world/grid setup
    grid_w = WORLD_W // TILE
    grid_h = WORLD_H // TILE

    # generate walls across the WORLD, but keep a safe radius around player start
    walls = pygame.sprite.Group()
    safe_radius_tiles = 4
    safe_rect = pygame.Rect(
        start_x - safe_radius_tiles * TILE,
        start_y - safe_radius_tiles * TILE,
        (safe_radius_tiles * 2) * TILE,
        (safe_radius_tiles * 2) * TILE,
    )
    for ty in range(grid_h):
        for tx in range(grid_w):
            x = tx * TILE
            y = ty * TILE
            # sparse random walls
            if random.random() < 0.12 and not safe_rect.colliderect(pygame.Rect(x, y, TILE, TILE)):
                walls.add(Wall(x, y))

    # blocked tiles set for pathfinding
    blocked_tiles = set()
    for w in walls:
        tx = w.rect.x // TILE
        ty = w.rect.y // TILE
        blocked_tiles.add((tx, ty))

    # spawn enemies randomly in the world avoiding walls and player safe area
    enemies = pygame.sprite.Group()
    spawn_attempts = 0
    while len(enemies) < 12 and spawn_attempts < 1000:
        spawn_attempts += 1
        ex = random.randint(0, WORLD_W - 20)
        ey = random.randint(0, WORLD_H - 20)
        r = pygame.Rect(ex, ey, 20, 20)
        # avoid walls and safe start area
        if safe_rect.colliderect(r):
            continue
        # simple overlap check with walls
        collides = False
        for w in walls:
            if r.colliderect(w.rect):
                collides = True
                break
        if collides:
            continue
        spd = random.uniform(0.6, 1.6)
        e = Enemy(ex, ey, spd, hp=2, size=20)
        enemies.add(e)

    # gameplay variables
    run = True
    attacking = False
    attack_timer = 0
    ATTACK_DURATION = 8
    ARC_ANGLE = math.pi / 6
    COOLDOWN = player.COOLDOWN
    DAMAGE_PER_HIT = 1
    KNOCKBACK_STRENGTH = 6.0

    # track player's tile to trigger path recalculation when they move tiles
    player_tile = (player.rect.centerx // TILE, player.rect.centery // TILE)

    # camera
    camera = Camera(SCREEN_W, SCREEN_H, WORLD_W, WORLD_H)

    while run:
        clock.tick(FPS)

        # EVENTS
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not attacking and player.cooldown_timer == 0:
                    attacking = True
                    attack_timer = ATTACK_DURATION

        # UPDATE
        player.update(walls)
        camera.center_on(player.rect)

        # detect if player moved to a different tile
        new_player_tile = (player.rect.centerx // TILE, player.rect.centery // TILE)
        player_moved_tile = new_player_tile != player_tile
        player_tile = new_player_tile

        # update enemies: path requests, movement, and state updates
        for e in list(enemies):
            e.tick_path_cooldown()
            if player_moved_tile or e.path_cooldown == 0:
                e.request_path(player.rect, blocked_tiles, grid_w, grid_h)
            if e.path:
                e.move_along_path()
            else:
                # fallback direct chase
                dx_e = player.rect.centerx - e.x
                dy_e = player.rect.centery - e.y
                dist = math.hypot(dx_e, dy_e)
                if dist != 0:
                    e.x += (dx_e / dist) * e.speed
                    e.y += (dy_e / dist) * e.speed
                    e.rect.center = (int(e.x), int(e.y))
            e.update(walls)

        # sword attack logic (now uses world mouse coords)
        sword_hitbox = None
        if attacking:
            mx, my = pygame.mouse.get_pos()
            world_mx, world_my = camera.to_world((mx, my))
            dir_x = world_mx - player.rect.centerx
            dir_y = world_my - player.rect.centery
            length_dir = math.hypot(dir_x, dir_y)
            if length_dir != 0:
                dir_x /= length_dir
                dir_y /= length_dir
            t = (ATTACK_DURATION - attack_timer) / ATTACK_DURATION
            angle_offset = (t - 0.5) * ARC_ANGLE
            sword_hitbox = get_mouse_sword_hitbox(player.rect, dir_x, dir_y, angle_offset)
            # cancel hitbox if it intersects a wall
            if sword_hitbox and rect_collides_walls(sword_hitbox, walls):
                sword_hitbox = None
            # apply damage and knockback to enemies hit
            if sword_hitbox:
                for e in list(enemies):
                    if sword_hitbox.colliderect(e.rect):
                        kb_dx = e.rect.centerx - player.rect.centerx
                        kb_dy = e.rect.centery - player.rect.centery
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
                            invul_frames=12,
                        )
                        if died:
                            enemies.remove(e)
            attack_timer -= 1
            if attack_timer <= 0:
                attacking = False
                player.cooldown_timer = COOLDOWN

        # DRAW
        screen.fill((0, 0, 0))

        # draw a simple world background grid for orientation (optional)
        grid_color = (30, 30, 30)
        # vertical lines
        for x in range(0, WORLD_W + 1, TILE * 4):
            pygame.draw.line(
                screen,
                grid_color,
                (x - camera.offset.x, 0 - camera.offset.y),
                (x - camera.offset.x, WORLD_H - camera.offset.y),
            )
        # horizontal lines
        for y in range(0, WORLD_H + 1, TILE * 4):
            pygame.draw.line(
                screen,
                grid_color,
                (0 - camera.offset.x, y - camera.offset.y),
                (WORLD_W - camera.offset.x, y - camera.offset.y),
            )

        # draw groups with camera
        camera.blit_group(screen, walls)
        camera.blit_group(screen, enemies)
        camera.blit_group(screen, player_group)

        # debug: draw remaining path nodes for each enemy
        for e in enemies:
            if e.path:
                for node in e.path[e.path_index:]:
                    cx = node[0] * TILE + TILE // 2
                    cy = node[1] * TILE + TILE // 2
                    pygame.draw.circle(screen, (100, 200, 255),
                                       (int(cx - camera.offset.x), int(cy - camera.offset.y)), 3)

        # sword hitbox debug (draw in screen space using offset)
        if sword_hitbox:
            debug_rect = pygame.Rect(sword_hitbox.x - camera.offset.x,
                                     sword_hitbox.y - camera.offset.y,
                                     sword_hitbox.width, sword_hitbox.height)
            pygame.draw.rect(screen, RED, debug_rect)

        # cooldown bar above player
        bar_w, bar_h = 40, 6
        bar_x = player.rect.centerx - bar_w // 2 - camera.offset.x
        bar_y = player.rect.top - 12 - camera.offset.y
        pygame.draw.rect(screen, GREY, (bar_x, bar_y, bar_w, bar_h))
        if player.cooldown_timer > 0:
            frac = player.cooldown_timer / COOLDOWN
            pygame.draw.rect(screen, (200, 50, 50), (bar_x, bar_y, int(bar_w * (1 - frac)), bar_h))
        else:
            pygame.draw.rect(screen, (50, 200, 50), (bar_x, bar_y, bar_w, bar_h))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
