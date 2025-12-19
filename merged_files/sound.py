import pygame

pygame.mixer.init()

sfx_combat_start = pygame.mixer.Sound('sounds\combat_start.ogg')

sfx_deur = pygame.mixer.Sound('sounds\deur.ogg')

sfx_minotaurus = pygame.mixer.Sound('sounds\minotaurus.ogg')
sfx_minotaurus.set_volume(.75)

sfx_pijl = pygame.mixer.Sound('sounds\pijl.ogg')

sfx_sfeergeluid = pygame.mixer.Sound('sounds\sfeergeluid1.ogg')

sfx_sleutel = pygame.mixer.Sound('sounds\sleutel_in_slot.ogg')

sfx_slime_dood = pygame.mixer.Sound('sounds\slime_dood.ogg')

sfx_slime_springt = pygame.mixer.Sound('sounds\slime_springt.ogg')

sfx_voetstappen = pygame.mixer.Sound('sounds\stappen.ogg')

sfx_zwaard = pygame.mixer.Sound('sounds\zwaard1.ogg')
sfx_zwaard.set_volume(.1)

sfx_punch = pygame.mixer.Sound('sounds\punch.ogg')
sfx_punch.set_volume(.1)

channel0 = pygame.mixer.Channel(0)
channel1 = pygame.mixer.Channel(1)
channel2 = pygame.mixer.Channel(2)
channel3 = pygame.mixer.Channel(3)
channel4 = pygame.mixer.Channel(4)
channel5 = pygame.mixer.Channel(5)