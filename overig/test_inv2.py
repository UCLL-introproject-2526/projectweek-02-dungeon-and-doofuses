import pygame
from game import Player, TILE, map_surface, screen

class KeyItem(pygame.sprite.Sprite):
    def __init__(self, x, y, key_id, size=12, color=(255, 215, 0)):
        super().__init__()
        self.key_id = key_id
        self.image = pygame.Surface([size, size], pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, (0, 0, size, size))
        self.rect = self.image.get_rect(center=(x, y))

class Door:
    def __init__(self, x, y, w, h, required_key):
        self.rect = pygame.Rect(x, y, w, h)
        self.required_key = required_key
        self.locked = True

    def unlock(self):
        self.locked = False

keys = pygame.sprite.Group()
keys.add(KeyItem(200, 150, key_id='gold'))

doors = []

doors.append(Door(10 ,10 ,10 ,10 , required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen
doors.append(Door(6*TILE, 4*TILE, TILE, TILE, required_key='gold')) # tiles veranderen


inventory = {}  # e.g., {'gold': 1}

for k in keys.sprites()[:]:
    if Player.colliderect(k.rect):
        keys.remove(k)
        inventory[k.key_id] = inventory.get(k.key_id, 0) + 1
        # optional: play pickup sound or flash

for d in doors[:]:
    screen.blit(map_surface)
    if d.locked and Player.colliderect(d.rect):
        if inventory.get(d.required_key, 0) > 0:
            # consume key to unlock
            inventory[d.required_key] -= 1
            if inventory[d.required_key] <= 0:
                del inventory[d.required_key]
            d.unlock()

font = pygame.font.Font(None, 20)
x = 8
for key_id, count in inventory.items():
    txt = f"{key_id}: {count}"
    screen.blit(map_surface(txt, True, (255,255,255)), (x, 8))
    x += 80


