def main():
    import pygame
    import random
    import math

    # -------------------- INIT --------------------
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    clock = pygame.time.Clock()

    # -------------------- COLORS --------------------
    PURP = (250, 0, 250)   # walls
    RED  = (250, 0, 0)     # sword hitbox (debug)
    YELL = (250, 250, 0)   # player

    # -------------------- PLAYER MOVEMENT FUNCTION --------------------
    def move_player(player, walls, px, py, dx, dy):
        # X axis
        px += dx
        player.x = int(px)
        if player.collidelist(walls) != -1:
            px -= dx
            player.x = int(px)

        # Y axis
        py += dy
        player.y = int(py)
        if player.collidelist(walls) != -1:
            py -= dy
            player.y = int(py)

        return px, py

    # -------------------- SWORD HITBOX (MOUSE AIMED) --------------------
    def get_mouse_sword_hitbox(player, dir_x, dir_y):
        reach = 28        # distance from player
        length = 24       # sword length
        thickness = 12    # sword width

        # center of sword in front of player
        cx = player.centerx + dir_x * reach
        cy = player.centery + dir_y * reach

        # choose orientation based on aim direction
        if abs(dir_x) > abs(dir_y):
            # horizontal slash
            return pygame.Rect(
                cx - length // 2,
                cy - thickness // 2,
                length,
                thickness
            )
        else:
            # vertical slash
            return pygame.Rect(
                cx - thickness // 2,
                cy - length // 2,
                thickness,
                length
            )

    # -------------------- PLAYER SETUP --------------------
    player = pygame.Rect(100, 100, 24, 24)
    px, py = float(player.x), float(player.y)

    # -------------------- DUNGEON WALLS --------------------
    TILE = 32
    walls = []

    for y in range(25):
        for x in range(25):
            if random.random() < 0.3:
                walls.append(
                    pygame.Rect(x * TILE, y * TILE, TILE, TILE)
                )

    # -------------------- GAME STATE --------------------
    speed = 2
    run = True

    # -------------------- ATTACK STATE --------------------
    attacking = False
    attack_timer = 0
    ATTACK_DURATION = 8   # frames sword is active

    # -------------------- MAIN LOOP --------------------
    while run:
        clock.tick(60)
        screen.fill((0, 0, 0))

        dx = dy = 0

        # -------------------- INPUT --------------------
        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            dx -= speed
        if keys[pygame.K_d]:
            dx += speed
        if keys[pygame.K_z]:
            dy -= speed
        if keys[pygame.K_s]:
            dy += speed

        # -------------------- MOVE PLAYER --------------------
        px, py = move_player(player, walls, px, py, dx, dy)

        # -------------------- SWORD ATTACK UPDATE --------------------
        sword_hitbox = None

        if attacking:
            mx, my = pygame.mouse.get_pos()

            # direction from player to mouse
            dir_x = mx - player.centerx
            dir_y = my - player.centery

            length = math.hypot(dir_x, dir_y)
            if length != 0:
                dir_x /= length
                dir_y /= length

            sword_hitbox = get_mouse_sword_hitbox(player, dir_x, dir_y)

            attack_timer -= 1
            if attack_timer <= 0:
                attacking = False

        # -------------------- DRAW --------------------
        pygame.draw.rect(screen, YELL, player)

        for wall in walls:
            pygame.draw.rect(screen, PURP, wall)

        # draw sword hitbox (debug)
        if sword_hitbox:
            pygame.draw.rect(screen, RED, sword_hitbox)

        # -------------------- EVENTS --------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not attacking:  # left click
                    attacking = True
                    attack_timer = ATTACK_DURATION

        pygame.display.flip()

    pygame.quit()

main()
