import pygame

class Menu():
    def __init__(self, game):
        self.game = game
        self.mid_w, self.mid_h = self.game.display_w/2, self.game.display_h/2
        self.run_display = True
        self.cursor_rectangle = pygame.Rect(0, 0, 20, 20)
        self.offset = -100

    def draw_cursor(self):
        self.game.draw_text('*', 15, self.cursor_rectangle.x, self.cursor_rectangle.y)

    def blit_screen(self):
        self.game.window.blit(self.game.display, (0,0))
        pygame.display.update()
        self.game.reset_keys()

class MainMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)
        self.state = 'Start'
        self.startx, self.starty = self.mid_w, self.mid_h + 30
        self.optionsx, self.optionsy = self.mid_w, self.mid_h + 50
        self.creditsx, self.creditsy = self.mid_w, self.mid_h + 70
        self.exitx, self.exity = self.mid_w, self.mid_h + 90
        self.cursor_rectangle.midtop = (self.startx + self.offset, self.starty)

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            self.check_input()
            self.game.display.fill(self.game.black)
            self.game.draw_text('Main Menu', 20, self.game.display_w/2, self.game.display_h/2 - 20)
            self.game.draw_text('Start Game', 20, self.startx, self.starty)
            self.game.draw_text('Options', 20, self.optionsx, self.optionsy)
            self.game.draw_text('Credits', 20, self.creditsx, self.creditsy)
            self.game.draw_text('Exit', 20, self.exitx, self.exity)
            self.draw_cursor()
            self.blit_screen()

    def move_cursor(self):
        if self.game.DOWN_KEY:
            self.game.nav_sound.play()
            if self.state == 'Start':
                self.cursor_rectangle.midtop = (self.optionsx + self.offset, self.optionsy)
                self.state = 'Options'
            elif self.state == 'Options':
                self.cursor_rectangle.midtop = (self.creditsx + self.offset, self.creditsy)
                self.state = 'Credits'
            elif self.state == 'Credits':
                self.cursor_rectangle.midtop = (self.exitx + self.offset, self.exity)
                self.state = "Exit"
            elif self.state == 'Exit':
                self.cursor_rectangle.midtop = (self.startx + self.offset, self.starty)
                self.state = "Start"
        elif self.game.UP_KEY:
            self.game.nav_sound.play()
            if self.state == 'Start':
                self.cursor_rectangle.midtop = (self.exitx + self.offset, self.exity)
                self.state = 'Exit'
            elif self.state == 'Options':
                self.cursor_rectangle.midtop = (self.startx + self.offset, self.starty)
                self.state = 'Start'
            elif self.state == 'Credits':
                self.cursor_rectangle.midtop = (self.optionsx + self.offset, self.optionsy)
                self.state = 'Options'
            elif self.state == 'Exit':
                self.cursor_rectangle.midtop = (self.creditsx + self.offset, self.creditsy)
                self.state = 'Credits'

    def check_input(self):
        self.move_cursor()
        if self.game.START_KEY:
            self.game.select_sound.play()
            if self.state == 'Start':
                self.game.playing = True
            elif self.state == 'Options':
                self.game.current_menu = self.game.options
            elif self.state == 'Credits':
                self.game.current_menu = self.game.credits
            elif self.state == 'Exit':
                self.game.running = False
                self.game.playing = False
                pygame.quit()
                quit()
            self.run_display = False

class OptionsMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)
        self.state = 'Volume'
        self.volx, self.voly = self.mid_w, self.mid_h + 20
        self.controlsx, self.controlsy = self.mid_w, self.mid_h + 40
        self.cursor_rectangle.midtop = (self.volx + self.offset, self.voly)

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            self.check_input()
            self.game.display.fill((0, 0, 0))
            self.game.draw_text('Options', 20, self.game.display_w/2, self.game.display_h/2 - 30)
            self.game.draw_text('Volume', 15, self.volx, self.voly)
            self.game.draw_text('Controls', 15, self.controlsx, self.controlsy)
            self.draw_cursor()
            self.blit_screen()

    def check_input(self):
        if self.game.BACK_KEY:
            self.game.goback_sound.play()
            self.game.current_menu = self.game.main_menu
            self.run_display = False
        elif self.game.UP_KEY or self.game.DOWN_KEY:
            self.game.nav_sound.play()
            if self.state == 'Volume':
                self.state = 'Controls'
                self.cursor_rectangle.midtop = (self.controlsx + self.offset, self.controlsy)
            elif self.state == 'Controls':
                self.state = 'Volume'
                self.cursor_rectangle.midtop = (self.volx + self.offset, self.voly)
        elif self.game.START_KEY:
            self.game.select_sound.play()
            if self.state == 'Volume':
                self.game.current_menu = self.game.volume_menu
            elif self.state == 'Controls':
                self.game.current_menu = self.game.controls_menu
            self.run_display = False

class VolumeMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            self.check_input()
            self.game.display.fill(self.game.black)
            self.game.draw_text('Volume', 20, self.game.display_w/2, self.game.display_h/2 - 30)
            volume_text = f'{self.game.volume} / 10'
            self.game.draw_text(volume_text, 20, self.game.display_w/2, self.game.display_h/2 + 10)
            self.blit_screen()
        
    def check_input(self):
        if self.game.LEFT_KEY and self.game.volume > 0:
            self.game.nav_sound.play()
            self.game.volume -= 1
            self.game.update_sound_volume()
            pygame.mixer.music.set_volume(self.game.volume/10)
        if self.game.RIGHT_KEY and self.game.volume < 10:
            self.game.nav_sound.play()
            self.game.volume += 1
            self.game.update_sound_volume()
            pygame.mixer.music.set_volume(self.game.volume/10)
        if self.game.BACK_KEY:
            self.game.goback_sound.play()
            self.game.current_menu = self.game.options
            self.run_display = False

class ControlsMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)

        size_keys = (48, 48)
        self.key_z = pygame.transform.scale(pygame.image.load('.\controls\z.png').convert_alpha(), size_keys)
        self.key_q = pygame.transform.scale(pygame.image.load('.\controls\q.png').convert_alpha(), size_keys)
        self.key_s = pygame.transform.scale(pygame.image.load('.\controls\s.png').convert_alpha(), size_keys)
        self.key_d = pygame.transform.scale(pygame.image.load('.\controls\d.png').convert_alpha(), size_keys)

        self.arrow_right = pygame.transform.scale(pygame.image.load('.\\arrow.png').convert_alpha(), (96, 96))

        self.mouse_click = pygame.transform.scale(pygame.image.load('.\mouse_controls\LeftClick-Blue.png').convert_alpha(), (64, 64))
        self.mouse_look = pygame.transform.scale(pygame.image.load('.\mouse_controls\MoveDiagonal.png').convert_alpha(), (96, 96))

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            self.check_input()
            self.game.display.fill(self.game.black)
            # x_postition = self.game.display_w - 160
            # y_position = self.game.display_h - 100

            self.game.display.blit(self.key_z, (90,10))
            self.game.display.blit(self.key_q, (45,55))
            self.game.display.blit(self.key_s, (90,55))
            self.game.display.blit(self.key_d, (135,55))
            self.game.draw_text('Move', 22, 360, 76)
            self.game.display.blit(self.arrow_right, (200,35))

            # mouse_y = start_y + spacing * 4 + 50
            self.game.display.blit(self.mouse_click, (80, 119))
            self.game.draw_text('Attack', 22, 360, 150)
            self.game.display.blit(self.mouse_look, (64, 180))
            self.game.draw_text('Aim', 22, 360, 220)
            self.game.display.blit(self.arrow_right, (200,107))
            self.game.display.blit(self.arrow_right, (200,179))

            self.blit_screen()

    def check_input(self):
        if self.game.BACK_KEY:
            self.game.goback_sound.play()
            self.game.current_menu = self.game.options
            self.run_display = False

class CreditsMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            if self.game.BACK_KEY:
                self.game.goback_sound.play()
                self.game.current_menu = self.game.main_menu
                self.run_display = False
            self.game.display.fill(self.game.black)
            self.game.draw_text('Credits', 20, self.game.display_w/2, self.game.display_h/2 - 20)
            self.game.draw_text('Made by Dungeon and Doofuses', 15, self.game.display_w/2, self.game.display_h/2 + 10)
            self.blit_screen()

class PauseMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)
        self.state = 'Resume'

        self.resumex, self.resumey = self.mid_w, self.mid_h - 10
        self.volx, self.voly = self.mid_w, self.mid_h + 10
        self.quitx, self.quity = self.mid_w, self.mid_h + 30

        self.cursor_rectangle.midtop = (self.resumex + self.offset, self.resumey)

    def draw_overlay(self):
        overlay = pygame.Surface((self.game.display_w, self.game.display_h))
        overlay.set_alpha(150) #0 = invisible, 255 = solid
        overlay.fill((0, 0, 0))
        self.game.display.blit(overlay, (0, 0))

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            self.check_input()
            self.draw_overlay()

            self.game.draw_text('Paused', 20, self.game.display_w/2, self.game.display_h/2 - 40)

            self.game.draw_text('Resume', 15, self.resumex, self.resumey)
            self.game.draw_text('Volume', 15, self.volx, self.voly)
            self.game.draw_text('Quit', 15, self.quitx, self.quity)

            self.draw_cursor()
            self.blit_screen()

    def move_cursor(self):
        if self.game.DOWN_KEY:
            self.game.nav_sound.play()
            if self.state == 'Resume':
                self.state = 'Volume'
                self.cursor_rectangle.midtop = (self.volx + self.offset, self.voly)
            elif self.state == 'Volume':
                self.state = 'Quit'
                self.cursor_rectangle.midtop = (self.quitx + self.offset, self.quity)
            elif self.state == 'Quit':
                self.state = 'Resume'
                self.cursor_rectangle.midtop = (self.resumex + self.offset, self.resumey)

        elif self.game.UP_KEY:
            self.game.nav_sound.play()
            if self.state == 'Resume':
                self.state = 'Quit'
                self.cursor_rectangle.midtop = (self.quitx + self.offset, self.quity)
            elif self.state == 'Volume':
                self.state = 'Resume'
                self.cursor_rectangle.midtop = (self.resumex + self.offset, self.resumey)
            elif self.state == 'Quit':
                self.state = 'Volume'
                self.cursor_rectangle.midtop= (self.volx + self.offset, self.voly)

    def check_input(self):
        self.move_cursor()

        if self.game.START_KEY:
            self.game.select_sound.play()

            if self.state == 'Resume':
                self.game.paused = False
                self.run_display = False

            elif self.state == 'Volume':
                self.game.current_menu = self.game.pause_volume_menu
                self.run_display = False

            elif self.state == 'Quit':
                self.game.paused = False
                self.game.playing = False
                self.game.current_menu = self.game.main_menu
                self.run_display = False

        if self.game.START_KEY and self.state == 'Resume':
            self.game.paused = False
            self.run_display = False

class PauseVolumeMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            self.check_input()
            self.game.display.fill(self.game.black)
            self.game.draw_text('Volume', 20, self.game.display_w/2, self.game.display_h/2 - 30)
            volume_text = f'{self.game.volume} / 10'
            self.game.draw_text(volume_text, 20, self.game.display_w/2, self.game.display_h/2 + 10)
            self.blit_screen()
        
    def check_input(self):
        if self.game.LEFT_KEY and self.game.volume > 0:
            self.game.nav_sound.play()
            self.game.volume -= 1
            self.game.update_sound_volume()
            pygame.mixer.music.set_volume(self.game.volume/10)
        if self.game.RIGHT_KEY and self.game.volume < 10:
            self.game.nav_sound.play()
            self.game.volume += 1
            self.game.update_sound_volume()
            pygame.mixer.music.set_volume(self.game.volume/10)
        if self.game.BACK_KEY:
            self.game.goback_sound.play()
            self.game.current_menu = self.game.pause_menu
            self.run_display = False

class GameOverMenu(Menu):
    def __init__(self, game):
        Menu.__init__(self, game)
        self.state = 'Yes'

        self.yesx, self.yesy = self.mid_w, self.mid_h + 20
        self.nox, self.noy = self.mid_w, self.mid_h + 40

        self.cursor_rectangle.midtop = (self.yesx + self.offset, self.yesy)

    def display_menu(self):
        self.run_display = True
        while self.run_display:
            self.game.check_events()
            self.check_input()

            self.game.display.fill(self.game.black)

            self.game.draw_text('GAME OVER', 25, self.game.display_w/2, self.game.display_h/2 - 40)

            self.game.draw_text('Play Again?', 15, self.game.display_w/2, self.game.display_h/2 - 10)

            self.game.draw_text('Yes', 15, self.yesx, self.yesy)
            self.game.draw_text('No', 15, self.nox, self.noy)

            self.draw_cursor()
            self.blit_screen()

    def move_cursor(self):
        if self.game.UP_KEY or self.game.DOWN_KEY:
            self.game.nav_sound.play()

        if self.state == 'Yes':
            self.state = 'No'
            self.cursor_rectangle.midtop = (self.yesx + self.offset, self.yesy)

    def check_input(self):
        self.move_cursor()

        if self.game.START_KEY:
            self.game.select_sound.play()

            if self.state == 'Yes':
                self.restart_game()
            elif self.state == 'No':
                self.game.current_menu = self.game.main_menu

            self.run_display = False

    def restart_game(self):
        self.game.game_over = False
        self.game.playing = True

        # Reset player, level, score here later
        # Example:
        # self.game.player.reset()

        self.game.current_menu = None