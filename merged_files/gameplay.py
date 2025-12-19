
# Patched game.py
# - No numpy/surfarray dependency (uses Surface.get_at for map sampling)
# - Windows path warnings fixed (pathlib/forward slashes)
# - Dynamic camera + AI preserved

from pathlib import Path
import pygame
import random
import math
import heapq

import sys

from sound import sfx_zwaard, sfx_voetstappen, sfx_punch

# ---------------------- CONFIG ----------------------
SCREEN_W, SCREEN_H = 1000, 600    # window size
TILE = 32                        # tile size for pathfinding grid
FPS = 60

# Asset paths (relative to this script)
ASSETS_DIR = Path('merged_files\Assets')
HERO_IMG = ASSETS_DIR / 'merged_files\Assets\Hero_basic_24x24.png'  # use your actual filename
MAP_IMG  = ASSETS_DIR / 'merged_files\Assets\map.png'          # pre-generated map image

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

def spawn_locations(free_tiles, amount, player):
    attempts = 0
    locations = 0
    free_tiles_list = list(free_tiles)
    result = set()
    while locations < amount and attempts < 1000:
        attempts += 1
        tx, ty = random.choice(free_tiles_list)
        ex = tx * TILE + TILE // 2
        ey = ty * TILE + TILE // 2
        if abs(ex - player.rect.centerx) + abs(ey - player.rect.centery) < TILE * 4:
            continue
        result.add((ex,ey))
        locations += 1
    return result

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
        self.image = pygame.image.load(str('Assets\img\Hero_basic_24x24.png')).convert_alpha()
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
        self.invincibility_duration = 1000
        self.vincible = False
        # movement key state for KEYDOWN/KEYUP handling
        self.move_left = False
        self.move_right = False
        self.move_up = False
        self.move_down = False
        self.moving = False  # last-frame moving state (for footstep sound)

    def handle_input(self):
        # Compute movement from stored key state (set by process_event)
        dx, dy = 0, 0
        if self.move_left:
            dx -= self.speed
        if self.move_right:
            dx += self.speed
        if self.move_up:
            dy -= self.speed
        if self.move_down:
            dy += self.speed

        moving_now = (dx != 0 or dy != 0)
        # Play footsteps only when movement starts
        if moving_now and not self.moving and not pygame.mixer.get_busy():
            sfx_voetstappen.play()
        self.moving = moving_now
        return dx, dy

    def process_event(self, event):
        """Call from the main event loop to track KEYDOWN/KEYUP state for smooth movement."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                self.move_left = True
            elif event.key == pygame.K_d:
                self.move_right = True
            elif event.key == pygame.K_z:
                self.move_up = True
            elif event.key == pygame.K_s:
                self.move_down = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_q:
                self.move_left = False
            elif event.key == pygame.K_d:
                self.move_right = False
            elif event.key == pygame.K_z:
                self.move_up = False
            elif event.key == pygame.K_s:
                self.move_down = False

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
        if self.vincible:
            if pygame.time.get_ticks() - self.last_hit > self.invincibility_duration:
                self.vincible = False

    def take_damage(self, amount):
        current_time = pygame.time.get_ticks()
        if not self.vincible:
            self.hp -= amount
            self.vincible = True
            self.last_hit = current_time
        if self.hp <= 0: self.die()

    def die(self):
        print("Speler is verslagen!")
        self.kill() # Verwijdert de speler uit alle groepen

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, speed, damage, hp=2):
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
        self.damage = damage

    def give_damage(self):
        return self.damage

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

class FastEnemy(Enemy):
    def __init__(self, x, y,speed,damage, hp=1, size=15):
        super().__init__(x, y, speed,damage, hp, size)
        self.speed *= 1.5
        self.image.fill((0, 0, 255))

    def give_damage(self):
        return self.damage
    
class vampireLord(Enemy):
    def __init__(self, x, y, speed, damage, hp=2,size = 20):
        super().__init__(x,y,speed, damage,hp,size)
        self.spawn_cooldown = 180

    def update(self,walls):
        super().update(walls)
        events = []
        self.spawn_cooldown -=1
        if self.spawn_cooldown == 0:
            events.append(("vampire", self.x,self.y, self.speed))
            self.spawn_cooldown = 180
        return events

class Boss(Enemy):
    def __init__(self, x, y, speed, damage, hp, size):
        super().__init__(x, y, speed, damage, hp, size)
        self.charge_allowed = False
        self.aoe_cooldown = 180  # frames tussen AoE
        self.charge_cooldown = 240  # frames tussen charges
        self.aoe_radius = 80
        self.aoe_timer = 0
        self.charge_timer = 0
        self.charging = False
        self.charge_speed = 6.0
        self.charge_dx = 0
        self.charge_dy = 0


    def area_of_effect(self, player):
        if self.aoe_cooldown > 0:
            return
        dx = player.rect.centerx - self.x
        dy = player.rect.centery - self.y
        dist = math.hypot(dx, dy)
        if dist <= self.aoe_radius:
              # schade + knockback
            kb_x = dx / dist if dist != 0 else 0
            kb_y = dy / dist if dist != 0 else -1
            player.take_damage(self.damage)
            player.x += kb_x * 10
            player.y += kb_y * 10
            player.rect.center = (int(player.x), int(player.y))
            print("Boss AoE hits player!")
        self.aoe_timer = self.aoe_cooldown

    def charge(self, player):
        target_x,target_y = player.rect.center
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx,dy)
        if distance == 0: return
        dx = dx/distance
        dy = dy/distance
        self.charge_dx = (dx / distance) * self.charge_speed
        self.charge_dy = (dy / distance) * self.charge_speed
        self.charging = True
        self.charge_timer = self.charge_cooldown
        print("Boss starts charging!") 



class Tank(Enemy):
    def __init__(self, x, y, speed,damage, hp=5, size=40):
        super().__init__(x, y, speed,damage, hp, size)
           
    
class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, speed=3, damage=1):
        super().__init__()
        self.image = pygame.Surface((6, 6))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))

        self.x = float(x)
        self.y = float(y)
        self.dx = dx
        self.dy = dy
        self.speed = speed
        self.damage = damage
        self.life = 180  # frames

    def update(self, walls):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.rect.center = (int(self.x), int(self.y))

        self.life -= 1
        if self.life <= 0:
            self.kill()
        if pygame.sprite.spritecollideany(self, walls):
            self.kill()
    
    def give_damage(self):
        return self.damage

class RangedEnemy(Enemy):
    def __init__(self, x, y, speed, hp=3, size=20):
        super().__init__(x, y, speed, hp, size)
        self.image.fill((255, 100, 0))
        self.shooting_range = TILE * 5
        self.shooting_cooldown = 120

    def update(self, walls):
        super().update(walls)
        events = []
        self.shooting_cooldown -= 1
        if self.shooting_cooldown == 0:
            events.append(("shoot",self.x,self.y ))
            self.shooting_cooldown = 180
        return events
    
    def give_damage(self):
        return 1
class Wall(pygame.sprite.Sprite):
    def __init__(self, rect):
        super().__init__()
        self.rect = rect.copy()
        # Semi-transparent debug overlay (comment out draw if not needed)
        self.image = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        self.image.fill((250, 0, 250, 80))

class Room (pygame.sprite.Sprite):
    def __init__(self,roomid, x, y, w, h, doors):
        super().__init__()
        self.id = roomid
        self.rect = pygame.Rect(x, y ,w ,h)
        self.cleared = False
        self.triggered = False
        #just to make sure only one wave spawns
        self.count = 0
        #self.doors is supposed to be a iterable
        self.doors = doors
        self.tiles = {
            (tx, ty)
            for tx in range(self.rect.left // TILE, self.rect.right // TILE)
            for ty in range(self.rect.top // TILE, self.rect.bottom // TILE)
        }
    def contains(self,player):
        return pygame.sprite.collide_rect(self,player)
    
    def unlock(self,blocked_tiles,walls):
        for d in self.doors:
            d.open(blocked_tiles,walls)

    def lock(self,blocked_tiles,walls):
        for d in self.doors:
            d.close(blocked_tiles,walls)

class Door(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, TILE=32):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill((100, 100, 100))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.x = x
        self.y = y

        self.opened = True
        self.timer = -1
        

        # compute covered tiles
        tx0 = x // TILE
        ty0 = y // TILE
        tw = w // TILE
        th = h // TILE

        self.tiles = [(tx0 + dx, ty0 + dy) for dy in range(th) for dx in range(tw)]
        self.wall_sprites = [Wall(pygame.Rect(tx*TILE, ty*TILE, TILE, TILE)) for (tx, ty) in self.tiles]

    def start_timer(self, seconds =1):
        if self.opened and self.timer == -1:
            self.timer = seconds * 60


    
    def close(self, blocked_tiles, walls):
        if  self.opened:
            for tile in self.tiles:
                blocked_tiles.add(tile)
            for sprite in self.wall_sprites:
                walls.add(sprite)
            self.opened = False

    def open(self, blocked_tiles, walls):
        """Manually open the door"""
        for tile in self.tiles:
            blocked_tiles.discard(tile)
        for sprite in self.wall_sprites:
            walls.remove(sprite)
        self.opened = True
        self.timer = 0

    def update(self, blocked_tiles, walls):
        if self.timer > 0:
            self.timer -= 1
            if self.timer == 0:
                self.close(blocked_tiles, walls)
                self.timer = -1


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
    font = pygame.font.Font('Assets\8-BIT WONDER.TTF', 30)
    menu_state = 'Main'

    options = ['Resume', 'Volume', 'Quit']
    state_index = 0

    mid_w, mid_h = screen.get_width()//2, screen.get_height()//2
    offset = -130

    while paused:
        clock.tick(60)

        for event in pygame.event.get():
            if menu_state == 'Volume':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s and game.volume > 0:
                        game.nav_sound.play()
                        game.volume -= 1
                        game.update_sound_volume()

                    elif event.key == pygame.K_z and game.volume < 10:
                        game.nav_sound.play()
                        game.volume += 1
                        game.update_sound_volume()

                    elif event.key == pygame.K_BACKSPACE or event.key == pygame.K_ESCAPE:
                        game.goback_sound.play()
                        menu_state = 'Main'

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = False

                elif event.key == pygame.K_z:
                    state_index = (state_index - 1) % len(options)
                    game.nav_sound.play()

                elif event.key == pygame.K_s:
                    state_index = (state_index + 1) % len(options)
                    game.nav_sound.play()

                elif event.key == pygame.K_RETURN:
                    game.select_sound.play()
                    choice = options[state_index]
                    if choice == 'Resume':
                        return 'Resume'
                    elif choice == 'Volume':
                        menu_state = 'Volume'
                    elif choice == 'Quit':
                        return 'Quit'

        overlay = pygame.Surface((1000, 600))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        if menu_state == 'Main':
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

        elif menu_state == 'Volume':
            title = font.render('Volume', True, (255, 255, 255))
            value = font.render(f'{game.volume} / 10', True, (255, 255, 255))

            screen.blit(title, title.get_rect(center=(mid_w, mid_h - 40)))
            screen.blit(value, value.get_rect(center=(mid_w, mid_h + 10)))

        pygame.display.flip()
    
    return 'Resume'


def main(game):
    pygame.init()
    pygame.display.set_caption('Game')
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    # Load sword sprite AFTER display init
    SWORD_IMG = pygame.image.load("Assets\img\Sword.png").convert_alpha()
    SWORD_IMG = pygame.transform.scale_by(SWORD_IMG, 0.1)  # scale sword

    # Load key sprite sheet (try several common paths). If not found, fallback to None.
    key_sheet = None
    key_sheet = pygame.image.load(str('Assets\img\key.png')).convert_alpha()
    key_frames = []
    KEY_ANIM_SPEED = 8  # frames per sprite frame
    KEY_SCALE = 0.1     # render key much smaller
    key_frame_index = 0
    key_anim_counter = 0
    if key_sheet:
        kw, kh = key_sheet.get_size()
        if kh >= kw and kw > 0:
            n = kh // kw
            for i in range(n):
                frame = key_sheet.subsurface(pygame.Rect(0, i * kw, kw, kw)).copy()
                frame = pygame.transform.scale_by(frame, KEY_SCALE)
                key_frames.append(frame)

    # Font for HUD (8-BIT WONDER)
    HUD_FONT = pygame.font.Font(str(Path('Assets') / '8-BIT WONDER.TTF'), 20)
   

    # Load map image (Path -> str)
    map_surface = pygame.image.load(str('Assets\img\map.png')).convert()
    # scale pixel art (x2)
    map_surface = pygame.transform.scale_by(map_surface, 2)

    # Load spike sprite sheet (for door decoration). Try common filenames.
    spike_sheet = None
    spike_sheet = pygame.image.load(str('Assets\img\spikes activate.png')).convert_alpha()
    spike_frames = []
    if spike_sheet:
        sw, sh = spike_sheet.get_size()
        if sh >= sw and sw > 0:
            # vertical strip -> take first square frame
            frame = spike_sheet.subsurface(pygame.Rect(0, 0, sw, sw)).copy()
            frame = pygame.transform.scale_by(frame, 0.1)
            spike_frames.append(frame)

    # Build world from map without surfarray
    world_w, world_h, grid_w, grid_h, blocked_tiles, walls = build_world_from_map(
        map_surface, TILE=TILE, alpha_threshold=8
    )
    world_rect = pygame.Rect(0, 0, world_w, world_h)

    # Camera uses real map size
    camera = Camera(SCREEN_W, SCREEN_H, world_w, world_h)

    pygame.mixer.init()
    pygame.mixer.music.load('sounds\muziek.ogg')
    pygame.mixer.music.play(loops=-1)
    pygame.mixer.music.set_volume(.3)

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

    # keys collected by clearing rooms (don't count boss room)
    current_keys = 0

   # make rooms and doors
    enemies = pygame.sprite.Group()
    rooms = pygame.sprite.Group()
    Doors = pygame.sprite.Group()
    Projectile_group = pygame.sprite.Group()
    door1room1 = Door(1346,1293,72,149)
    door2room1 = Door(478,577,99,91)  
    door1room2 = Door(1629,3555,100,88)
    door2room2 = Door(766,3021,95,148) 
    door1room3 = Door(3459,3597,89,146)
    door2room3 = Door(3458,3787,89,152)
    door1room4 = Door(3453,2085,100,73)
    door2room4 = Door(3839,2110,98,50)
    door1room5 = Door(3279,907,79,153)    
    bossdoor = Door(2302,866,196,53)
    
    door1 = [door1room1,door2room1]
    door2 = [door1room2,door2room2]
    door3 = [door1room3,door2room3]
    door4 = [door1room4,door2room4]
    door5 = [door1room5] 

    door_boss = [bossdoor]
    Doors.add(bossdoor)
    Doors.add(door1room1)
    Doors.add(door2room1)
    Doors.add(door1room2)
    Doors.add(door2room2)
    Doors.add(door1room3)
    Doors.add(door2room3)
    Doors.add(door1room4)
    Doors.add(door2room4)
    Doors.add(door1room5)
    # Make non-boss door images invisible 
    # for d in Doors:
    #     if d is bossdoor:
    #         continue
    #     d.image = pygame.Surface((d.rect.width, d.rect.height), pygame.SRCALPHA)
    #     d.image.fill((0, 0, 0, 0))
    
    rooms.add(Room("room1_fix",477,671,880,880,door1))
    rooms.add(Room("room4_fix",3358,2157,675,720,door4))
    rooms.add(Room("room5_fix",3359,333,865,818,door5))
    rooms.add(Room("room2_fix",863,2829,960,723,door2))
    rooms.add(Room("room3_fix",3551,3500,769,629,door3))
    rooms.add(Room("boss",1631,45,1538,819,door_boss))

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
    current_room = None
    

    run = True
    paused = False
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            # let the player track key state for smooth movement
            player.process_event(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not attacking and player.cooldown_timer == 0:
                    attacking = True
                    attack_timer = ATTACK_DURATION

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                   paused = True 

            if paused:
                pygame.event.clear(pygame.KEYDOWN)
                result = pause_game(screen, clock, game)
            

                if result == 'Quit':
                    return
                
                paused = False
                continue
        # Update
        # save previous player position to prevent entering boss room without enough keys
        prev_player_x, prev_player_y = player.x, player.y
        player.update(walls, world_rect)
        camera.center_on(player.rect)

        new_player_tile = (player.rect.centerx // TILE, player.rect.centery // TILE)
        player_moved_tile = new_player_tile != player_tile
        player_tile = new_player_tile

        for e in list(enemies):
            e.tick_path_cooldown()
            if player_moved_tile or e.path_cooldown == 0:
                e.request_path(player.rect, blocked_tiles, grid_w, grid_h)
            # save previous position to allow reverting on collision 
            old_x, old_y = e.x, e.y
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

            # call update (this may apply knockback)d
            e.update(walls, world_rect)

            # collision with walls, player, or other enemies -> revert to previous position and cancel knockback
            collided = False
            if pygame.sprite.spritecollideany(e, walls):
                collided = True
            elif e.rect.colliderect(player.rect):
                collided = True
            else:
                for other in enemies:
                    if other is e:
                        continue
                    if e.rect.colliderect(other.rect):
                        collided = True
                        break
            if collided:
                e.x, e.y = old_x, old_y
                e.rect.center = (int(e.x), int(e.y))
                e.kb_vx = 0.0
                e.kb_vy = 0.0

        arrow  = pygame.sprite.spritecollideany(player, Projectile_group) 
        if arrow:
            player.take_damage(arrow.give_damage())
            arrow.kill()

        mon = pygame.sprite.spritecollideany( player, enemies)
        if mon: player.take_damage(mon.give_damage())
        sword_hitbox = None
        if attacking:
            mx, my = pygame.mouse.get_pos()
            world_mx, world_my = camera.to_world((mx, my))
            dir_x = world_mx - player.rect.centerx
            dir_y = world_my - player.rect.centery
            length_dir = math.hypot(dir_x, dir_y)
            if pygame.mixer.get_busy() == False:
               sfx_zwaard.play()
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
                        sfx_punch.play() 
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

        for room in rooms:
            # Check of de speler binnenstapt EN of de kamer nog niet geactiveerd was
            if not room.triggered and room.contains(player):
                # Boss room requires 5 keys to enter
                if room.id == 'boss' and current_keys < 5:
                    # revert player position to previous frame (prevent entering)
                    player.x, player.y = prev_player_x, prev_player_y
                    player.rect.topleft = (int(player.x), int(player.y))
                    continue
                room.triggered = True  # Zorg dat dit direct op True gaat
                current_room = room

                # Start de timer voor alle deuren van deze kamer
                for door in room.doors:
                    door.start_timer(1) # 1 seconde

        # Update alle deuren (dit zorgt voor het aftellen)
        for door in Doors:
            door.update(blocked_tiles, walls)

        if current_room:
            if not current_room.doors[0].opened and current_room.count == 0:
                current_room.count = 1
                free_tiles = current_room.tiles - blocked_tiles
                locations = spawn_locations(free_tiles,10,player)
                for location in locations:
                    ex,ey = location
                    enemies.add(Enemy(ex,ey,2,1))
        
        if current_room and current_room.count == 1 and len(enemies) == 0:
            # Only increment once when the room is first cleared
            if not current_room.cleared:
                if current_room.id != 'boss':
                    current_keys += 1
                current_room.cleared = True
            current_room.unlock(blocked_tiles,walls)

        # Draw
        screen.fill((0, 0, 0))
        screen.blit(map_surface, (-camera.offset.x, -camera.offset.y))
        # Debug: draw collision tiles overlay
        # for w in walls:
        #     screen.blit(w.image, (w.rect.x - camera.offset.x, w.rect.y - camera.offset.y))
        camera.blit_group(screen, enemies)
        camera.blit_group(screen, player_group)
        camera.blit_group(screen,Doors)
        camera.blit_group(screen,Projectile_group)

        # Draw spike decoration for non-boss doors (one spike frame per door tile)
        # for d in Doors:
        #     if d is bossdoor:
        #         continue
        #     else:
        #         px = d.x - camera.offset.x 
        #         py = d.y - camera.offset.y + 50
        #         screen.blit(spike_frames[0], (px, py))

        # for w in walls:
        #     screen.blit(w.image, (w.rect.x - camera.offset.x, w.rect.y))


         # ---------------- SWORD VISUAL ----------------
        if sword_hitbox:
            # Angle from mouse direction (visual only)
            angle_deg = math.degrees(math.atan2(-dir_y, dir_x))
            angle_deg += -90 # adjust sword img rotation 

            # Rotate sword sprite (does NOT affect collision)
            rotated_sword = pygame.transform.rotate(SWORD_IMG, angle_deg)

            # Draw sword centered on hitbox
            sword_rect = rotated_sword.get_rect(
                center=(
                    sword_hitbox.centerx - camera.offset.x,
                    sword_hitbox.centery - camera.offset.y
                )
            )

            screen.blit(rotated_sword, sword_rect)


        # Debug: sword rect
        if sword_hitbox:
            debug_rect = pygame.Rect(sword_hitbox.x - camera.offset.x,
                                     sword_hitbox.y - camera.offset.y,
                                     sword_hitbox.width, sword_hitbox.height)
            # pygame.draw.rect(screen, (250, 0, 0), debug_rect, 1)

        # Cooldown bar
        # bar_w, bar_h = 40, 6
        # bar_x = player.rect.centerx - bar_w // 2 - camera.offset.x
        # bar_y = player.rect.top - 12 - camera.offset.y
        # pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h))
        # if player.cooldown_timer > 0:
        #     frac = player.cooldown_timer / COOLDOWN
        #     pygame.draw.rect(screen, (200, 50, 50), (bar_x, bar_y, int(bar_w * (1 - frac)), bar_h))
        # else:
        #     pygame.draw.rect(screen, (50, 200, 50), (bar_x, bar_y, bar_w, bar_h))

        # Draw keys HUD (bottom-left) — only during gameplay (pause uses its own menu)
        if key_frames:
            key_anim_counter += 1
            if key_anim_counter >= KEY_ANIM_SPEED:
                key_anim_counter = 0
                key_frame_index = (key_frame_index + 1) % len(key_frames)
            key_img = key_frames[key_frame_index]
            k_w, k_h = key_img.get_size()
            hud_x = 8
            hud_y = screen.get_height() - k_h - 8
            screen.blit(key_img, (hud_x, hud_y))
            # render number next to key
            txt = HUD_FONT.render(str(current_keys), True, (255, 255, 255))
            screen.blit(txt, (hud_x + k_w + 6, hud_y + (k_h - txt.get_height()) // 2))
        else:
            # fallback: draw a simple yellow key rectangle and number
            hud_x = 8
            hud_y = screen.get_height() - 16 - 8
            pygame.draw.rect(screen, (220, 200, 20), (hud_x, hud_y, 16, 8))
            txt = HUD_FONT.render(str(current_keys), True, (255, 255, 255))
            screen.blit(txt, (hud_x + 22, hud_y - 2))

        pygame.display.flip()

    # pygame.quit()
    return
