
# Patched game.py
# - No numpy/surfarray dependency (uses Surface.get_at for map sampling)
# - Windows path warnings fixed (pathlib/forward slashes)
# - Dynamic camera + AI preserved

from pathlib import Path
import pygame
import random
import math
import heapq
from menu_game import *
import sys

# ---------------------- CONFIG ----------------------
SCREEN_W, SCREEN_H = 1000, 600    # window size
TILE = 32                        # tile size for pathfinding grid
FPS = 60

# Asset paths (relative to this script)
ASSETS_DIR = Path('Merged/Assets')
HERO_IMG = ASSETS_DIR / 'Assets\Hero_basic_24x24.png'  # use your actual filename
MAP_IMG  = ASSETS_DIR / 'Assets\map.png'          # pre-generated map image

# ---------------------- CAMERA ----------------------
class Camera:
    def __init__(self, screen_w, screen_h, world_w, world_h):
        self.offset = pygame.math.Vector2(0, 0)
        self.half_w = screen_w // 2
        self.half_h = screen_h // 2
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.world_w = world_w
        self.world_h = world_h

    def center_on(self, target_rect):
        target_x = target_rect.centerx - self.half_w
        target_y = target_rect.centery - self.half_h
        # Direct set (snappy). Swap with lerp for smoothing.
        self.offset.x = max(0, min(target_x, self.world_w - self.screen_w))
        self.offset.y = max(0, min(target_y, self.world_h - self.screen_h))

    def to_world(self, screen_pos):
        return (screen_pos[0] + int(self.offset.x), screen_pos[1] + int(self.offset.y))

    def blit_group(self, surface, group):
        for sprite in sorted(group.sprites(), key=lambda s: s.rect.centery):
            surface.blit(sprite.image, (sprite.rect.x - self.offset.x,
                                        sprite.rect.y - self.offset.y))

# ---------------------- UTILITIES -------------------
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

def rect_collides_walls(rect, walls_group):
    for w in walls_group:
        if rect.colliderect(w.rect):
            return True
    return False

# ---------------------- A* PATHFINDING ---------------
def astar(start, goal, blocked, grid_w, grid_h):
    if start == goal:
        return []

    def h(a, b):
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return math.sqrt(dx*dx + dy*dy)  # Euclidean heuristic

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
            path = []
            node = current
            while node != start:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path
        closed.add(current)
        cx, cy = current
        neighbors = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
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
    return []

# ---------------------- SPRITES ----------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=5, max_hp=10, cooldown=4):
        super().__init__()
        # Load hero sprite (Path -> str)
        self.image = pygame.image.load(str('Assets\Hero_basic_24x24.png')).convert_alpha()
        # scale pixel art (x2)
        self.image = pygame.transform.scale_by(self.image, 2)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        self.max_hp = max_hp
        self.hp = max_hp
        self.cooldown_timer = 0
        self.COOLDOWN = cooldown

    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_q]: dx -= self.speed
        if keys[pygame.K_d]: dx += self.speed
        if keys[pygame.K_z]: dy -= self.speed
        if keys[pygame.K_s]: dy += self.speed
        return dx, dy

    def move(self, dx, dy, walls):
        self.x += dx
        self.rect.topleft = (int(self.x), int(self.y))
        if pygame.sprite.spritecollideany(self, walls):
            self.x -= dx
            self.rect.topleft = (int(self.x), int(self.y))
        self.y += dy
        self.rect.topleft = (int(self.x), int(self.y))
        if pygame.sprite.spritecollideany(self, walls):
            self.y -= dy
            self.rect.topleft = (int(self.x), int(self.y))

    def update(self, walls, world_rect):
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        dx, dy = self.handle_input()
        self.move(dx, dy, walls)
        self.rect.clamp_ip(world_rect)
        self.x, self.y = float(self.rect.left), float(self.rect.top)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, speed, hp=2):
        super().__init__()
        self.image = pygame.Surface([20, 20])
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        self.hp = hp
        self.invul = 0
        self.kb_vx = 0.0
        self.kb_vy = 0.0
        self.path = []
        self.path_index = 0
        self.path_cooldown = 0
        self.last_player_tile = None

    def update(self, walls, world_rect):
        if self.invul > 0:
            self.invul -= 1
            self.image.fill((200, 120, 120))
        else:
            self.image.fill((0, 255, 0))
        if abs(self.kb_vx) > 0.01 or abs(self.kb_vy) > 0.01:
            self.x += self.kb_vx
            self.y += self.kb_vy
            self.rect.center = (int(self.x), int(self.y))
            if pygame.sprite.spritecollideany(self, walls):
                self.x -= self.kb_vx
                self.y -= self.kb_vy
                self.rect.center = (int(self.x), int(self.y))
                self.kb_vx = 0
                self.kb_vy = 0
            self.kb_vx *= 0.8
            self.kb_vy *= 0.8
        self.rect.center = (int(self.x), int(self.y))
        self.rect.clamp_ip(world_rect)
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
    def __init__(self, rect):
        super().__init__()
        self.rect = rect.copy()
        # Semi-transparent debug overlay (comment out draw if not needed)
        self.image = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        self.image.fill((250, 0, 250, 80))

# ---------------------- MAP LOADING -----------------

def build_world_from_map(map_surface, TILE=32, alpha_threshold=8):
    world_w, world_h = map_surface.get_size()
    grid_w = world_w // TILE
    grid_h = world_h // TILE

    blocked_tiles = set()

    map_surface.lock()
    try:
        for ty in range(grid_h):
            for tx in range(grid_w):
                sx = tx * TILE + TILE // 2
                sy = ty * TILE + TILE // 2
                if sx >= world_w:  sx = world_w - 1
                if sy >= world_h:  sy = world_h - 1
                r, g, b, *_ = map_surface.get_at((sx, sy))
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                if lum > alpha_threshold:
                    blocked_tiles.add((tx, ty))
    finally:
        map_surface.unlock()

    walls = pygame.sprite.Group()
    for (tx, ty) in blocked_tiles:
        rect = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
        walls.add(Wall(rect))

    return world_w, world_h, grid_w, grid_h, blocked_tiles, walls

# ---------------------- MAIN -------------------------
def pause_game(screen, clock, game):
    pygame.init()
    paused = True
    font = pygame.font.Font('8-BIT WONDER.TTF', 30)

    options = ['Resume', 'Volume', 'Quit']
    state_index = 0

    mid_w, mid_h = screen.get_width()//2, screen.get_height()//2
    offset = -130

    while paused:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = False

                elif event.key == pygame.K_UP:
                    state_index = (state_index - 1) % len(options)
                    game.nav_sound.play()

                elif event.key == pygame.K_DOWN:
                    state_index = (state_index + 1) % len(options)
                    game.nav_sound.play()

                elif event.key == pygame.K_RETURN:
                    game.select_sound.play()
                    choice = options[state_index]
                    if choice == 'Resume':
                        return 'Resume'
                    elif choice == 'Volume':
                        pass
                    elif choice == 'Quit':
                        return 'Quit'

        overlay = pygame.Surface((1000, 600))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        text = font.render('Paused', True, (255, 255, 255))
        rect = text.get_rect(center = (mid_w, mid_h - 60))
        screen.blit(text, rect)

        for i, option in enumerate(options):
            color = (255, 255, 255)
            text_surface = font.render(option, True, color)
            text_rectangle = text_surface.get_rect(center = (mid_w, mid_h + i * 40))
            screen.blit(text_surface, text_rectangle)

        cursor_x = mid_w + offset
        cursor_y = mid_h + state_index * 37
        pygame.draw.polygon(screen, (255, 255, 255), [(cursor_x, cursor_y), (cursor_x + 15, cursor_y + 10), (cursor_x, cursor_y + 20)])

        pygame.display.flip()


def main():
    pygame.init()
    pygame.display.set_caption('Game')
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    # Load map image (Path -> str)
    map_surface = pygame.image.load(str('Assets\map.png')).convert()
    # scale pixel art (x2)
    map_surface = pygame.transform.scale_by(map_surface, 2)

    # Build world from map without surfarray
    world_w, world_h, grid_w, grid_h, blocked_tiles, walls = build_world_from_map(
        map_surface, TILE=TILE, alpha_threshold=8
    )
    world_rect = pygame.Rect(0, 0, world_w, world_h)

    # Camera uses real map size
    camera = Camera(SCREEN_W, SCREEN_H, world_w, world_h)

    # Player start: first free tile near top-left
    start_tx, start_ty = 70,70
    if (start_tx, start_ty) in blocked_tiles:
        found = False
        for ty in range(grid_h):
            for tx in range(grid_w):
                if (tx, ty) not in blocked_tiles:
                    start_tx, start_ty = tx, ty
                    found = True
                    break
            if found:
                break
    start_x = start_tx * TILE + TILE // 4
    start_y = start_ty * TILE + TILE // 4
    player = Player(start_x, start_y)
    player_group = pygame.sprite.GroupSingle(player)

    # Enemies: spawn on random free tiles
    enemies = pygame.sprite.Group()
    attempts = 0
    while len(enemies) < 10 and attempts < 1000:
        attempts += 1
        tx = random.randint(0, grid_w - 1)
        ty = random.randint(0, grid_h - 1)
        if (tx, ty) in blocked_tiles:
            continue
        ex = tx * TILE + TILE // 2
        ey = ty * TILE + TILE // 2
        if abs(ex - player.rect.centerx) + abs(ey - player.rect.centery) < TILE * 4:
            continue
        spd = random.uniform(0.6, 1.6)
        enemies.add(Enemy(ex, ey, spd, hp=2))

    # Combat state
    attacking = False
    attack_timer = 0
    ATTACK_DURATION = 8
    ARC_ANGLE = math.pi / 6
    COOLDOWN = player.COOLDOWN
    DAMAGE_PER_HIT = 1
    KNOCKBACK_STRENGTH = 6.0

    # Track player's tile for path recompute
    player_tile = (player.rect.centerx // TILE, player.rect.centery // TILE)

    run = True
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not attacking and player.cooldown_timer == 0:
                    attacking = True
                    attack_timer = ATTACK_DURATION

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from menu_game import Game
                    game = Game()
                    result = pause_game(screen, clock, game)
                    if result == 'Quit': 
                        return
            
        # Update
        player.update(walls, world_rect)
        camera.center_on(player.rect)

        new_player_tile = (player.rect.centerx // TILE, player.rect.centery // TILE)
        player_moved_tile = new_player_tile != player_tile
        player_tile = new_player_tile

        for e in list(enemies):
            e.tick_path_cooldown()
            if player_moved_tile or e.path_cooldown == 0:
                e.request_path(player.rect, blocked_tiles, grid_w, grid_h)
            if e.path:
                e.move_along_path()
            else:
                dx_e = player.rect.centerx - e.x
                dy_e = player.rect.centery - e.y
                dist = math.hypot(dx_e, dy_e)
                if dist != 0:
                    e.x += (dx_e / dist) * e.speed
                    e.y += (dy_e / dist) * e.speed
                    e.rect.center = (int(e.x), int(e.y))
            e.update(walls, world_rect)

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
            if sword_hitbox and rect_collides_walls(sword_hitbox, walls):
                sword_hitbox = None
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

        # Draw
        screen.fill((0, 0, 0))
        screen.blit(map_surface, (-camera.offset.x, -camera.offset.y))
        # Debug: draw collision tiles overlay
        # for w in walls:
        #     screen.blit(w.image, (w.rect.x - camera.offset.x, w.rect.y - camera.offset.y))
        camera.blit_group(screen, enemies)
        camera.blit_group(screen, player_group)

        # for w in walls:
        #     screen.blit(w.image, (w.rect.x - camera.offset.x, w.rect.y))



        # Debug: sword rect
        if sword_hitbox:
            debug_rect = pygame.Rect(sword_hitbox.x - camera.offset.x,
                                     sword_hitbox.y - camera.offset.y,
                                     sword_hitbox.width, sword_hitbox.height)
            pygame.draw.rect(screen, (250, 0, 0), debug_rect, 1)

        # Cooldown bar
        bar_w, bar_h = 40, 6
        bar_x = player.rect.centerx - bar_w // 2 - camera.offset.x
        bar_y = player.rect.top - 12 - camera.offset.y
        pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h))
        if player.cooldown_timer > 0:
            frac = player.cooldown_timer / COOLDOWN
            pygame.draw.rect(screen, (200, 50, 50), (bar_x, bar_y, int(bar_w * (1 - frac)), bar_h))
        else:
            pygame.draw.rect(screen, (50, 200, 50), (bar_x, bar_y, bar_w, bar_h))

        pygame.display.flip()

    # pygame.quit()
    return
