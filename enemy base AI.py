import pygame
import random
import math
from math import hypot
import heapq

# -------------------- CONFIGURATION --------------------
SCREEN_W, SCREEN_H = 500, 500
TILE = 32                      # tile size used for walls and pathfinding
FPS = 60

# -------------------- UTILITIES --------------------
# Helper functie: compute an axis-aligned sword rect in front of player
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


# -------------------- A STAR PATHFINDING --------------------
def astar(start, goal, blocked, grid_w, grid_h):
    # ... (A* code blijft hetzelfde, omdat deze al goed was) ...
    if start == goal:
        return []

    def h(a, b):
        x_squared = (a[0]-b[0])**2
        y_squared = (a[1]-b[1])**2
        return math.sqrt(x_squared+y_squared) #trying euclidian heuristic
        #return abs(a[0] - b[0]) + abs(a[1] - b[1])   # Manhattan heuristic

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
        # Gebruik alleen 4 buren (niet diagonaal)
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

    return [] # no path found

# -------------------- PLAYER SPRITE --------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, size=24, speed=2, max_hp=10, cooldown=4):
        super().__init__()
        self.size = size
        self.image = pygame.Surface([size, size])
        self.image.fill((250, 250, 0))  # YELL
        self.rect = self.image.get_rect(topleft=(x, y))
        
        # Float positie voor soepele beweging
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        
        # Gezondheid
        self.max_hp = max_hp
        self.hp = max_hp
        
        # Combat state (voor de cooldown timer)
        self.cooldown_timer = 0
        self.COOLDOWN = cooldown
        self.is_attacking = False
        
    def handle_input(self):
        """Lees de toetsenbord-input en bereken de gewenste beweging."""
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        # Je had K_q, K_d, K_z, K_s (AZERTY/QWERTY?)
        if keys[pygame.K_q]: dx -= self.speed
        if keys[pygame.K_d]: dx += self.speed
        if keys[pygame.K_z]: dy -= self.speed
        if keys[pygame.K_s]: dy += self.speed
        return dx, dy

    def move(self, dx, dy, walls):
        """Pas beweging toe en los botsingen op met muren."""
        
        # Oplossing van de oude helper functie move_player, maar dan object-georiënteerd
        
        # X-as beweging
        self.x += dx
        self.rect.topleft = (int(self.x), int(self.y))
        
        # Pygame.sprite.spritecollideany werkt met groepen!
        if pygame.sprite.spritecollideany(self, walls):
            self.x -= dx # Terugzetten
            self.rect.topleft = (int(self.x), int(self.y))

        # Y-as beweging
        self.y += dy
        self.rect.topleft = (int(self.x), int(self.y))
        if pygame.sprite.spritecollideany(self, walls):
            self.y -= dy # Terugzetten
            self.rect.topleft = (int(self.x), int(self.y))

    def update(self, walls):
        """Update de speler state, inclusief input, beweging en cooldowns."""
        
        # 1. Cooldown tick
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        
        # 2. Beweging
        dx, dy = self.handle_input()
        self.move(dx, dy, walls)
        
        # 3. Klem binnen scherm
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_W, SCREEN_H))
        self.x, self.y = float(self.rect.left), float(self.rect.top)

    def take_damage(self, amount):
        # Basis schade-logica voor de speler (kan worden uitgebreid met invul/schade-flash)
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        print("Speler is verslagen!")
        self.kill() # Verwijdert de speler uit alle groepen


# -------------------- ENEMY SPRITE WITH PATHFINDING --------------------
# ... (Enemy klasse blijft hetzelfde) ...
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

    def update(self, walls): # Muren toegevoegd om knockback-botsing te kunnen controleren
        """Update visual state and apply knockback decay each frame."""
        if self.invul > 0:
            self.invul -= 1
            self.image.fill((200, 120, 120))  # flash color when invulnerable
        else:
            self.image.fill((0, 255, 0))

        # apply knockback and decay it
        if abs(self.kb_vx) > 0.01 or abs(self.kb_vy) > 0.01:
            
            # Voer knockback uit
            self.x += self.kb_vx
            self.y += self.kb_vy
            self.rect.center = (int(self.x), int(self.y))
            
            # Controleer botsing met muren
            if pygame.sprite.spritecollideany(self, walls):
                # Als het botst, zet dan de positie terug
                self.x -= self.kb_vx
                self.y -= self.kb_vy
                self.rect.center = (int(self.x), int(self.y))
                self.kb_vx = 0 # stop de knockback
                self.kb_vy = 0
            
            # Verminder knockback
            self.kb_vx *= 0.8
            self.kb_vy *= 0.8
        
        # sync rect with float position
        self.rect.center = (int(self.x), int(self.y))
        
        # Clamp inside screen and sync float pos
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_W, SCREEN_H))
        self.x, self.y = float(self.rect.centerx), float(self.rect.centery)


    def move_along_path(self):
        # ... (deze methode blijft hetzelfde) ...
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
        # ... (deze methode blijft hetzelfde) ...
        if self.path_cooldown > 0:
            return

        my_tile = (int(self.x) // TILE, int(self.y) // TILE)
        player_tile = (player_rect.centerx // TILE, player_rect.centery // TILE)

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
        # ... (deze methode blijft hetzelfde) ...
        if self.path_cooldown > 0:
            self.path_cooldown -= 1

    def take_damage(self, amount, kb_x=0.0, kb_y=0.0, invul_frames=12):
        # ... (deze methode blijft hetzelfde) ...
        if self.invul > 0:
            return False
        self.hp -= amount
        self.invul = invul_frames
        self.kb_vx += kb_x
        self.kb_vy += kb_y
        return self.hp <= 0


class Wall(pygame.sprite.Sprite):
    def __init__(self,x,y):
        super().__init__()
        # Opmerking: TILE in de config is 32. Je gebruikt 50 hier, 
        # maar voor de consistentie met TILE heb ik de grootte van de Surface veranderd naar TILE
        size = TILE 
        self.image = pygame.Surface([size, size]) 
        self.image.fill((250, 0, 250))
        self.rect = self.image.get_rect()
        
        # De rects moeten op de linkerhoek van de tile staan, niet in het midden
        self.rect.topleft = (x, y) 

    
# -------------------- MAIN GAME --------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    # colors used in drawing
    PURP = (250, 0, 250) 
    RED  = (250, 0, 0)
    YELL = (250, 250, 0)
    GREY = (80, 80, 80)

    # LET OP: de oude 'move_player' helper-functie is nu vervangen door Player.move()
    # De 'get_mouse_sword_hitbox' functie is nu globaal (zie UTILITIES)

    # player setup (NU: EEN INSTANTIE VAN DE PLAYER KLASSE!)
    player_size = 24
    start_x, start_y = 100, 100
    player = Player(start_x, start_y, size=player_size)
    player_group = pygame.sprite.GroupSingle(player) # Gebruik GroupSingle

    # generate dungeon walls, skipping the player's starting tile
    walls = pygame.sprite.Group() # Dit is nu de Pygame Group voor efficiënte botsing
    
    grid_w = SCREEN_W // TILE
    grid_h = SCREEN_H // TILE
    
    # We lopen over de tiles, niet over 25x25, want scherm is 500x500
    for y in range(grid_h): 
        for x in range(grid_w):
            if random.random() < 0.2 and abs(x*TILE - start_x) > TILE*2 and abs(y*TILE - start_y) > TILE*2:
                walls.add(Wall(x * TILE, y * TILE))

    # build blocked tile set for pathfinding from walls
    blocked_tiles = set()
    for w in walls:
        tx = w.rect.x // TILE # Gebruik rect.x/y want de Wall sprite is nu juist gepositioneerd
        ty = w.rect.y // TILE
        blocked_tiles.add((tx, ty))

    # spawn enemies as sprites, avoiding walls and player
    enemies = pygame.sprite.Group()
    spawn_attempts = 0
    while len(enemies) < 8 and spawn_attempts < 500:
        spawn_attempts += 1
        ex = random.randint(0, SCREEN_W - 20)
        ey = random.randint(0, SCREEN_H - 20)
        r = pygame.Rect(ex, ey, 20, 20)
        
        # Controleer botsing met WallGroup
        # Zorg dat de spawn niet in een muur zit
        temp_wall_check = Wall(r.x, r.y)
        temp_wall_check.rect.topleft = (r.x, r.y)
        
        if not pygame.sprite.spritecollideany(temp_wall_check, walls) and not r.colliderect(player.rect):
             spd = random.uniform(0.6, 1.6)
             e = Enemy(ex, ey, spd, hp=2, size=20)
             enemies.add(e)
        del temp_wall_check
    
    # gameplay variables
    run = True

    # attack state (gebruik nu de player instance om de state bij te houden)
    attacking = False
    attack_timer = 0
    ATTACK_DURATION = 8
    ARC_ANGLE = math.pi / 6 
    COOLDOWN = player.COOLDOWN
    
    DAMAGE_PER_HIT = 1
    KNOCKBACK_STRENGTH = 6.0

    # track player's tile to trigger path recalculation when they move tiles
    player_tile = (player.rect.centerx // TILE, player.rect.centery // TILE)

    # -------------------- MAIN LOOP --------------------
    while run:
        clock.tick(FPS)
        screen.fill((0, 0, 0))

        # OUDE INPUT/BEWEGING IS NU PLAYER.UPDATE()
        player.update(walls) 

        # detect if player moved to a different tile
        new_player_tile = (player.rect.centerx // TILE, player.rect.centery // TILE)
        player_moved_tile = new_player_tile != player_tile
        player_tile = new_player_tile

        # update enemies: path requests, movement, and state updates
        for e in list(enemies):
            e.tick_path_cooldown()

            # request a new path if player moved tile or cooldown expired
            if player_moved_tile or e.path_cooldown == 0:
                e.request_path(player.rect, blocked_tiles, grid_w, grid_h)

            # follow path if available, otherwise fallback to direct chase
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
            
            # apply invul/knockback visuals and check collision with walls
            e.update(walls) # NU met de walls groep

            # clamp inside screen and sync float pos
            e.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_W, SCREEN_H))
            e.x, e.y = float(e.rect.centerx), float(e.rect.centery)


        # sword attack logic
        sword_hitbox = None
        if attacking:
            mx, my = pygame.mouse.get_pos()
            dir_x = mx - player.rect.centerx # Gebruik player.rect
            dir_y = my - player.rect.centery
            length_dir = math.hypot(dir_x, dir_y)
            if length_dir != 0:
                dir_x /= length_dir
                dir_y /= length_dir

            t = (ATTACK_DURATION - attack_timer) / ATTACK_DURATION
            angle_offset = (t - 0.5) * ARC_ANGLE
            sword_hitbox = get_mouse_sword_hitbox(player.rect, dir_x, dir_y, angle_offset) # Gebruik player.rect

            # cancel hitbox if it intersects a wall
            # VROEGER: collidelist(walls) - NU: spritecollideany(walls)
            if sword_hitbox and pygame.sprite.spritecollideany(Wall(sword_hitbox.x, sword_hitbox.y), walls):
                 sword_hitbox = None

            # apply damage and knockback to enemies hit
            if sword_hitbox:
                for e in list(enemies):
                    if sword_hitbox.colliderect(e.rect):
                        kb_dx = e.rect.centerx - player.rect.centerx
                        kb_dy = e.rect.centery - player.rect.centery
                        kb_len = math.hypot(kb_dx, kb_dy)
                        # ... (rest van de knockback berekening blijft hetzelfde) ...
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
                player.cooldown_timer = COOLDOWN # Gebruik de timer van de speler

        # cooldown tick (DEZE LOGICA IS VERPLAATST NAAR PLAYER.UPDATE())
        # if cooldown_timer > 0: cooldown_timer -= 1

        # -------------------- DRAW --------------------
        
        # walls (nu via de groep)
        walls.draw(screen)

        # player
        player_group.draw(screen)

        # enemies
        enemies.draw(screen)

        # debug: draw remaining path nodes for each enemy
        for e in enemies:
            if e.path:
                for node in e.path[e.path_index:]:
                    cx = node[0] * TILE + TILE // 2
                    cy = node[1] * TILE + TILE // 2
                    pygame.draw.circle(screen, (100, 200, 255), (cx, cy), 3)

        # sword hitbox debug
        if sword_hitbox:
            pygame.draw.rect(screen, RED, sword_hitbox)

        # cooldown bar above player (gebruik nu de timer van de speler)
        bar_w, bar_h = 40, 6
        bar_x = player.rect.centerx - bar_w // 2
        bar_y = player.rect.top - 12
        pygame.draw.rect(screen, GREY, (bar_x, bar_y, bar_w, bar_h))
        if player.cooldown_timer > 0:
            frac = player.cooldown_timer / COOLDOWN
            pygame.draw.rect(screen, (200, 50, 50), (bar_x, bar_y, int(bar_w * (1 - frac)), bar_h))
        else:
            pygame.draw.rect(screen, (50, 200, 50), (bar_x, bar_y, bar_w, bar_h))

        # -------------------- EVENTS --------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not attacking and player.cooldown_timer == 0:
                    attacking = True
                    attack_timer = ATTACK_DURATION

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()