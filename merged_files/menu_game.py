import pygame
import gameplay
from menu import *

class Game():
    def __init__(self):
        pygame.init()
        self.running, self.playing = True, False
        self.UP_KEY, self.DOWN_KEY, self.START_KEY, self.BACK_KEY = False, False, False, False
        self.LEFT_KEY, self.RIGHT_KEY = False, False
        self.ESCAPE_KEY = False
        self.display_w, self.display_h = 1000, 600
        self.display = pygame.Surface((self.display_w,self.display_h))
        self.window = pygame.display.set_mode((self.display_w,self.display_h))
        self.font_name = 'Assets\8-BIT WONDER.TTF'
        # self.font_name = pygame.font.get_default_font()
        self.black, self.white = (0, 0, 0), (255, 255, 255)
        self.main_menu = MainMenu(self)
        self.options = OptionsMenu(self)
        self.volume_menu = VolumeMenu(self)
        self.controls_menu = ControlsMenu(self)
        self.credits = CreditsMenu(self)
        self.game_over_menu = GameOverMenu(self)
        self.victory_menu = VictoryMenu(self)
        self.current_menu = self.main_menu
        self.next_action = None

        self.paused = False
        # self.pause_menu = PauseMenu(self)
        # self.pause_volume_menu = PauseVolumeMenu(self)

        self.game_over = False
        # self.game_over_menu = GameOverMenu(self)

        self.volume = 5
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume/10)

        pygame.mixer.music.load('Assets\Music\main_menu_cut.mp3')
        pygame.mixer.music.play(-1)

        self.nav_sound = pygame.mixer.Sound('Assets\Music\main_menu_nav.wav')
        self.select_sound = pygame.mixer.Sound('Assets\Music\main_menu_select_cut.wav')
        self.goback_sound = pygame.mixer.Sound('Assets\Music\main_menu_goback_cut.wav')
        self.update_sound_volume()

    # def game_loop(self):
    #     while self.playing:
    #         self.check_events()
    #         if self.paused:
    #             self.current_menu.display_menu()
    #             continue
    #         if self.START_KEY:
    #             self.playing = False
    #         # self.display.fill(self.black)
    #         # self.draw_text('Thanks for playing', 20, self.display_w/2, self.display_h/2)
    #         # self.window.blit(self.display, (0,0))
    #         pygame.display.update()
    #         self.reset_keys()

    # def player_died(self):
    #     self.game_over = True
    #     self.playing = False
    #     self.current_menu = self.game_over_menu

    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running, self.playing = False, False
                self.current_menu.run_display = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.START_KEY = True
                if event.key == pygame.K_BACKSPACE:
                    self.BACK_KEY = True
                if event.key == pygame.K_s:
                    self.DOWN_KEY = True
                if event.key == pygame.K_z:
                    self.UP_KEY = True
                if event.key == pygame.K_q:
                    self.LEFT_KEY = True
                if event.key == pygame.K_d:
                    self.RIGHT_KEY = True
                if event.key == pygame.K_ESCAPE:
                    if self.playing:
                        self.paused = True
                        self.current_menu = self.pause_menu
    def reset_keys(self):
        self.UP_KEY, self.DOWN_KEY, self.START_KEY, self.BACK_KEY = False, False, False, False
        self.LEFT_KEY, self.RIGHT_KEY = False, False
        self.ESCAPE_KEY = False

    def draw_text(self, text, size, x, y):
        pygame.init()
        font = pygame.font.Font(self.font_name,size)
        text_surface = font.render(text, True, self.white)
        text_rectangle = text_surface.get_rect()
        text_rectangle.center = (x,y)
        self.display.blit(text_surface,text_rectangle)

    def update_sound_volume(self):
        volume = self.volume/10
        self.nav_sound.set_volume(volume)
        self.select_sound.set_volume(volume)
        self.goback_sound.set_volume(volume)
        pygame.mixer.music.set_volume(volume)

    def run_gameplay(self):
        pygame.mixer.music.stop()
        result = gameplay.main(self)
        if result == "GAME_OVER":
            self.current_menu = self.game_over_menu
        elif result == "VICTORY":
            self.current_menu = self.victory_menu
        else:
            self.current_menu = self.main_menu
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load('Assets\Music\main_menu_cut.mp3')
        pygame.mixer.music.set_volume(self.volume/10)
        pygame.mixer.music.play(-1)