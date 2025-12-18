from menu_game import Game
import pygame
import sys

pygame.init()

g = Game()

while g.running:
    g.current_menu.display_menu()
    if g.next_action == 'Start':
        g.run_gameplay()

        g.next_action = None
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            