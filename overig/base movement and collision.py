def main():
    import pygame
    import random

    # -------------------- INIT --------------------
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    clock = pygame.time.Clock()

    # -------------------- COLORS --------------------
    PURP = (250, 0, 250)   # walls
    RED  = (250, 0, 0)     # player when colliding
    YELL = (250, 250, 0)   # normal player

    # -------------------- PLAYER MOVEMENT FUNCTION --------------------

    # Moves the player with axis-separated collision.
    # This prevents clipping through walls and allows smooth sliding.

    def move_player(player, walls, px, py, dx, dy):
        # ---- X AXIS MOVE ----
        px += dx                 # apply horizontal movement
        player.x = int(px)       # sync rect with float position

        # if colliding, undo the movement
        if player.collidelist(walls) != -1:
            px -= dx
            player.x = int(px)

        # ---- Y AXIS MOVE ----
        py += dy                 # apply vertical movement
        player.y = int(py)

        # if colliding, undo the movement
        if player.collidelist(walls) != -1:
            py -= dy
            player.y = int(py)

        return px, py             # return corrected float position


    # -------------------- PLAYER SETUP --------------------
    # Player is slightly smaller than a tile for smoother movement
    player = pygame.Rect(100, 100, 24, 24)

    # Float position for smooth movement
    px, py = float(player.x), float(player.y)


    # -------------------- DUNGEON WALLS --------------------
    TILE = 32                   # grid tile size
    walls = []


    # Random dungeon layout (placeholder for real rooms later)
    for y in range(25):
        for x in range(25):
            if random.random() < 0.3:   # 30% chance of wall
                walls.append(
                    pygame.Rect(x * TILE, y * TILE, TILE, TILE)
                )



    # -------------------- GAME STATE --------------------
    speed = 2                   # movement speed
    col = YELL                  # player color
    run = True


    # -------------------- MAIN GAME LOOP --------------------
    while run:
        clock.tick(60)          # cap FPS
        screen.fill((0, 0, 0))  # clear screen

        # Reset movement every frame
        dx = dy = 0


        # -------------------- INPUT --------------------
        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            dx -= speed         # move left
        if keys[pygame.K_d]:
            dx += speed         # move right
        if keys[pygame.K_z]:
            dy -= speed         # move up
        if keys[pygame.K_s]:
            dy += speed         # move down



        # -------------------- MOVEMENT + COLLISION --------------------
        px, py = move_player(player, walls, px, py, dx, dy)


        # -------------------- DRAW --------------------
        pygame.draw.rect(screen, col, player)

        for wall in walls:
            pygame.draw.rect(screen, PURP, wall)


        # -------------------- EVENTS --------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        pygame.display.flip()

    pygame.quit()

main()
