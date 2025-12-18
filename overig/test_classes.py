import pygame
from math import hypot
from test_inventory import InventoryView, Inventory


class enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, speed):
        super().__init__ ()
        self.image = pygame.Surface([50,50])
        self.image.fill((0,255,0))
        self.rect = self.image.get_rect()
        self.rect.center = (x,y)
        self.speed = speed

    def move_to_player(self,rect):
        x_change =  rect.centerx - self.rect.centerx 
        y_change =  rect.centery - self.rect.centery

        afstand = hypot(x_change, y_change)
        if afstand == 0: return

        self.rect.centerx += (x_change/afstand)*self.speed
        self.rect.centery += (y_change/afstand)*self.speed




        
    def update(self,player):
       hitbox = player.rect
       self.move_to_player(hitbox)
       

class player(pygame.sprite.Sprite):
    def __init__(self,):
        super().__init__()
        self.image = pygame.Surface([50,50])
        self.image.fill((255,0,0))
        self.rect = self.image.get_rect()
        self.rect.center = (400,200)


    def update(self):
        pass

    def input(self):
        pass
pygame.init()
screen = pygame.display.set_mode((800,400))
Player = pygame.sprite.GroupSingle()
user = player()
Player.add(user)

Monster = pygame.sprite.Group()
Monster.add(enemy(700,350, 1))

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:  running = False

    Player.draw(screen)
    Monster.draw(screen)
    for monster in Monster:
        print(monster.rect.centerx)
    Monster.update(user)
    pygame.display.update()
pygame.quit()