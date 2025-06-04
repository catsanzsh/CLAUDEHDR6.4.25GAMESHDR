import pygame
import sys
import math
import random

# Initialize pygame
pygame.init()

# Game Boy screen dimensions and scale
GB_WIDTH, GB_HEIGHT = 160, 144
SCALE = 4  # Scale up for modern displays
WIDTH, HEIGHT = GB_WIDTH * SCALE, GB_HEIGHT * SCALE
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario Land - Game Boy")

# Game Boy color palette (4 colors)
GB_DARKEST = (15, 56, 15)      # Darkest green
GB_DARK = (48, 98, 48)         # Dark green  
GB_LIGHT = (139, 172, 15)      # Light green
GB_LIGHTEST = (155, 188, 15)   # Lightest green

# Game constants
FPS = 60
GRAVITY = 0.3
PLAYER_SPEED = 1.5
JUMP_STRENGTH = 4.5
SCROLL_THRESH = GB_WIDTH // 3

# Font (scaled for Game Boy resolution)
font = pygame.font.Font(None, 16)

class Sprite:
    """Base sprite class with pixel art drawing"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.surface = pygame.Surface((GB_WIDTH, GB_HEIGHT))
        self.surface.fill(GB_LIGHTEST)
        
    def draw_pixel(self, x, y, color):
        """Draw a single pixel scaled up"""
        pygame.draw.rect(self.surface, color, 
                        (x, y, 1, 1))

class Player(Sprite):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.width = 8
        self.height = 8
        self.vel_y = 0
        self.jumping = False
        self.direction = 1
        self.animation_frame = 0
        self.invincible = 0
        self.lives = 3
        self.coins = 0
        self.active = True
        
    def move(self, dx, platforms, enemies, coins):
        if not self.active:
            return
            
        # Horizontal movement
        self.x += dx
        if dx != 0:
            self.direction = 1 if dx > 0 else -1
            self.animation_frame += 0.2
            if self.animation_frame >= 2:
                self.animation_frame = 0
        
        # Platform collision (horizontal)
        for platform in platforms:
            if self.collision(platform):
                if dx > 0:
                    self.x = platform.x - self.width
                else:
                    self.x = platform.x + platform.width
        
        # Gravity
        self.vel_y += GRAVITY
        self.y += self.vel_y
        
        # Platform collision (vertical)
        on_ground = False
        for platform in platforms:
            if self.collision(platform):
                if self.vel_y > 0:  # Falling
                    self.y = platform.y - self.height
                    self.vel_y = 0
                    self.jumping = False
                    on_ground = True
                elif self.vel_y < 0:  # Jumping
                    self.y = platform.y + platform.height
                    self.vel_y = 0
        
        # Enemy collision
        for enemy in enemies:
            if enemy.active and self.collision(enemy):
                if self.vel_y > 0 and self.y < enemy.y:
                    # Stomp enemy
                    enemy.active = False
                    self.vel_y = -JUMP_STRENGTH * 0.6
                    self.coins += 1
                elif self.invincible <= 0:
                    # Take damage
                    self.invincible = 60
                    self.lives -= 1
                    if self.lives <= 0:
                        self.active = False
        
        # Coin collection
        for coin in coins[:]:
            if self.collision(coin):
                coins.remove(coin)
                self.coins += 1
        
        # Keep player in bounds
        if self.y > GB_HEIGHT:
            self.active = False
    
    def collision(self, obj):
        return (self.x < obj.x + obj.width and
                self.x + self.width > obj.x and
                self.y < obj.y + obj.height and
                self.y + self.height > obj.y)
    
    def jump(self):
        if not self.jumping:
            self.vel_y = -JUMP_STRENGTH
            self.jumping = True
    
    def draw(self, surface, scroll_x):
        if not self.active:
            return
            
        if self.invincible > 0:
            if self.invincible % 6 < 3:
                return
            self.invincible -= 1
        
        x_pos = int(self.x - scroll_x)
        y_pos = int(self.y)
        
        # Mario sprite (8x8 pixels)
        mario_pixels = [
            # Frame 1 (standing/walking 1)
            [
                [0,0,1,1,1,0,0,0],
                [0,1,1,1,1,1,0,0],
                [0,1,2,2,2,1,0,0],
                [0,2,2,2,2,2,0,0],
                [0,0,1,1,1,0,0,0],
                [0,1,1,1,1,1,0,0],
                [0,1,0,0,0,1,0,0],
                [0,1,0,0,0,1,0,0]
            ],
            # Frame 2 (walking 2)
            [
                [0,0,1,1,1,0,0,0],
                [0,1,1,1,1,1,0,0],
                [0,1,2,2,2,1,0,0],
                [0,2,2,2,2,2,0,0],
                [0,0,1,1,1,0,0,0],
                [0,1,1,1,1,1,0,0],
                [0,0,1,0,1,0,0,0],
                [0,1,0,0,0,1,0,0]
            ]
        ]
        
        # Select frame
        frame = int(self.animation_frame) if abs(self.vel_y) < 0.1 else 0
        pixels = mario_pixels[frame]
        
        # Flip if facing left
        if self.direction < 0:
            pixels = [row[::-1] for row in pixels]
        
        # Draw Mario
        for y in range(8):
            for x in range(8):
                if pixels[y][x] > 0:
                    if pixels[y][x] == 1:
                        color = GB_DARK
                    else:
                        color = GB_DARKEST
                    if 0 <= x_pos + x < GB_WIDTH and 0 <= y_pos + y < GB_HEIGHT:
                        surface.set_at((x_pos + x, y_pos + y), color)

class Platform:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def draw(self, surface, scroll_x):
        x_pos = int(self.x - scroll_x)
        y_pos = int(self.y)
        
        # Draw platform with tile pattern
        for ty in range(0, self.height, 8):
            for tx in range(0, self.width, 8):
                self.draw_tile(surface, x_pos + tx, y_pos + ty)
    
    def draw_tile(self, surface, x, y):
        # 8x8 platform tile
        tile = [
            [1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,1],
            [1,0,1,1,1,1,0,1],
            [1,0,1,0,0,1,0,1],
            [1,0,1,0,0,1,0,1],
            [1,0,1,1,1,1,0,1],
            [1,0,0,0,0,0,0,1],
            [1,1,1,1,1,1,1,1]
        ]
        
        for ty in range(8):
            for tx in range(8):
                if 0 <= x + tx < GB_WIDTH and 0 <= y + ty < GB_HEIGHT:
                    color = GB_DARK if tile[ty][tx] == 1 else GB_LIGHT
                    surface.set_at((x + tx, y + ty), color)

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 8
        self.height = 8
        self.direction = -1
        self.speed = 0.5
        self.active = True
        self.animation_frame = 0
    
    def move(self, platforms):
        if not self.active:
            return
            
        self.x += self.direction * self.speed
        self.animation_frame += 0.1
        if self.animation_frame >= 2:
            self.animation_frame = 0
        
        # Change direction at platform edges
        on_platform = False
        for platform in platforms:
            if (self.x + self.width > platform.x and 
                self.x < platform.x + platform.width and
                abs((self.y + self.height) - platform.y) < 2):
                on_platform = True
                
                if (self.direction < 0 and self.x <= platform.x) or \
                   (self.direction > 0 and self.x + self.width >= platform.x + platform.width):
                    self.direction *= -1
        
        if not on_platform:
            self.direction *= -1
    
    def draw(self, surface, scroll_x):
        if not self.active:
            return
            
        x_pos = int(self.x - scroll_x)
        y_pos = int(self.y)
        
        # Goomba sprite (8x8)
        goomba = [
            [0,0,1,1,1,1,0,0],
            [0,1,1,1,1,1,1,0],
            [0,1,0,1,1,0,1,0],
            [0,1,1,1,1,1,1,0],
            [0,1,1,0,0,1,1,0],
            [0,0,1,1,1,1,0,0],
            [0,1,0,0,0,0,1,0],
            [1,1,0,0,0,0,1,1]
        ]
        
        # Animate walking
        if int(self.animation_frame) == 1:
            goomba[7] = [1,0,1,0,0,1,0,1]
        
        # Draw goomba
        for y in range(8):
            for x in range(8):
                if goomba[y][x] == 1:
                    if 0 <= x_pos + x < GB_WIDTH and 0 <= y_pos + y < GB_HEIGHT:
                        surface.set_at((x_pos + x, y_pos + y), GB_DARK)

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 8
        self.height = 8
        self.animation_frame = 0
    
    def draw(self, surface, scroll_x):
        x_pos = int(self.x - scroll_x)
        y_pos = int(self.y)
        
        self.animation_frame += 0.1
        
        # Coin sprite (8x8) with animation
        coin = [
            [0,0,1,1,1,1,0,0],
            [0,1,1,1,1,1,1,0],
            [0,1,1,0,0,1,1,0],
            [0,1,1,0,0,1,1,0],
            [0,1,1,0,0,1,1,0],
            [0,1,1,0,0,1,1,0],
            [0,1,1,1,1,1,1,0],
            [0,0,1,1,1,1,0,0]
        ]
        
        # Animate (make it spin)
        if int(self.animation_frame) % 4 == 1:
            for y in range(8):
                coin[y] = [0,0,0,1,1,0,0,0]
        elif int(self.animation_frame) % 4 == 3:
            for y in range(8):
                coin[y] = [0,0,0,1,1,0,0,0]
        
        # Draw coin
        for y in range(8):
            for x in range(8):
                if coin[y][x] == 1:
                    if 0 <= x_pos + x < GB_WIDTH and 0 <= y_pos + y < GB_HEIGHT:
                        surface.set_at((x_pos + x, y_pos + y), GB_DARKEST)

class Goal:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 16
        self.height = 32
    
    def draw(self, surface, scroll_x):
        x_pos = int(self.x - scroll_x)
        y_pos = int(self.y)
        
        # Draw flag pole
        for y in range(32):
            if 0 <= x_pos + 7 < GB_WIDTH and 0 <= y_pos + y < GB_HEIGHT:
                surface.set_at((x_pos + 7, y_pos + y), GB_DARKEST)
                surface.set_at((x_pos + 8, y_pos + y), GB_DARKEST)
        
        # Draw flag
        flag = [
            [1,1,1,1,1,1,1,0],
            [1,0,0,0,0,0,1,0],
            [1,0,0,0,0,0,1,0],
            [1,1,1,1,1,1,1,0],
            [0,0,0,0,0,0,0,0]
        ]
        
        for y in range(5):
            for x in range(8):
                if flag[y][x] == 1:
                    if 0 <= x_pos + x + 9 < GB_WIDTH and 0 <= y_pos + y + 5 < GB_HEIGHT:
                        surface.set_at((x_pos + x + 9, y_pos + y + 5), GB_DARK)

class Level:
    def __init__(self, level_num):
        self.level_num = level_num
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.goal = None
        self.level_width = 640  # 4 screens wide
        self.player_start = (20, 100)
        
        self.create_level(level_num)
    
    def create_level(self, num):
        # Ground
        for x in range(0, self.level_width, 16):
            self.platforms.append(Platform(x, GB_HEIGHT - 16, 16, 16))
        
        if num == 1:
            # Level 1 - Simple
            self.platforms.append(Platform(80, 100, 32, 8))
            self.platforms.append(Platform(140, 80, 24, 8))
            self.platforms.append(Platform(200, 100, 40, 8))
            self.platforms.append(Platform(280, 90, 32, 8))
            
            self.enemies.append(Enemy(100, 92))
            self.enemies.append(Enemy(220, 92))
            
            self.coins.append(Coin(90, 85))
            self.coins.append(Coin(150, 65))
            self.coins.append(Coin(210, 85))
            
        elif num == 2:
            # Level 2 - More complex
            self.platforms.append(Platform(60, 110, 24, 8))
            self.platforms.append(Platform(100, 90, 32, 8))
            self.platforms.append(Platform(150, 100, 24, 8))
            self.platforms.append(Platform(190, 70, 40, 8))
            self.platforms.append(Platform(250, 90, 32, 8))
            self.platforms.append(Platform(300, 110, 40, 8))
            
            self.enemies.append(Enemy(70, 102))
            self.enemies.append(Enemy(160, 92))
            self.enemies.append(Enemy(200, 62))
            self.enemies.append(Enemy(310, 102))
            
            for i in range(6):
                self.coins.append(Coin(70 + i * 40, 50 + (i % 2) * 20))
                
        elif num == 3:
            # Level 3 - Challenging
            self.platforms.append(Platform(50, 100, 24, 8))
            self.platforms.append(Platform(90, 80, 24, 8))
            self.platforms.append(Platform(130, 110, 32, 8))
            self.platforms.append(Platform(180, 70, 24, 8))
            self.platforms.append(Platform(220, 90, 40, 8))
            self.platforms.append(Platform(280, 60, 32, 8))
            self.platforms.append(Platform(340, 100, 48, 8))
            
            self.enemies.append(Enemy(60, 92))
            self.enemies.append(Enemy(140, 102))
            self.enemies.append(Enemy(190, 62))
            self.enemies.append(Enemy(230, 82))
            self.enemies.append(Enemy(290, 52))
            self.enemies.append(Enemy(350, 92))
            
            for i in range(8):
                self.coins.append(Coin(60 + i * 35, 40 + (i % 3) * 15))
        
        # Goal at end of level
        self.goal = Goal(self.level_width - 40, GB_HEIGHT - 48)

class Game:
    def __init__(self):
        self.state = "menu"
        self.current_level = 1
        self.player = None
        self.level = None
        self.scroll_x = 0
        self.gb_surface = pygame.Surface((GB_WIDTH, GB_HEIGHT))
        self.level_unlocked = [True, False, False]
        
    def start_level(self, level_num):
        self.current_level = level_num
        self.level = Level(level_num)
        self.player = Player(*self.level.player_start)
        self.scroll_x = 0
        self.state = "playing"
    
    def draw_text(self, surface, text, x, y, color=GB_DARKEST):
        """Draw pixelated text"""
        char_width = 4
        char_map = {
            'A': [[1,1,1],[1,0,1],[1,1,1],[1,0,1]],
            'B': [[1,1,0],[1,0,1],[1,1,0],[1,1,1]],
            'C': [[1,1,1],[1,0,0],[1,0,0],[1,1,1]],
            'D': [[1,1,0],[1,0,1],[1,0,1],[1,1,0]],
            'E': [[1,1,1],[1,0,0],[1,1,0],[1,1,1]],
            'F': [[1,1,1],[1,0,0],[1,1,0],[1,0,0]],
            'G': [[1,1,1],[1,0,0],[1,0,1],[1,1,1]],
            'H': [[1,0,1],[1,0,1],[1,1,1],[1,0,1]],
            'I': [[1,1,1],[0,1,0],[0,1,0],[1,1,1]],
            'J': [[0,0,1],[0,0,1],[1,0,1],[1,1,1]],
            'K': [[1,0,1],[1,1,0],[1,1,0],[1,0,1]],
            'L': [[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
            'M': [[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            'N': [[1,0,1],[1,1,1],[1,1,1],[1,0,1]],
            'O': [[1,1,1],[1,0,1],[1,0,1],[1,1,1]],
            'P': [[1,1,1],[1,0,1],[1,1,1],[1,0,0]],
            'Q': [[1,1,0],[1,0,1],[1,1,0],[0,0,1]],
            'R': [[1,1,0],[1,0,1],[1,1,0],[1,0,1]],
            'S': [[1,1,1],[1,0,0],[0,1,0],[1,1,1]],
            'T': [[1,1,1],[0,1,0],[0,1,0],[0,1,0]],
            'U': [[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
            'V': [[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'W': [[1,0,1],[1,0,1],[1,1,1],[1,0,1]],
            'X': [[1,0,1],[0,1,0],[0,1,0],[1,0,1]],
            'Y': [[1,0,1],[1,0,1],[0,1,0],[0,1,0]],
            'Z': [[1,1,1],[0,0,1],[0,1,0],[1,1,1]],
            '0': [[1,1,1],[1,0,1],[1,0,1],[1,1,1]],
            '1': [[0,1,0],[1,1,0],[0,1,0],[1,1,1]],
            '2': [[1,1,1],[0,0,1],[0,1,0],[1,1,1]],
            '3': [[1,1,1],[0,0,1],[0,1,1],[1,1,1]],
            ' ': [[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
            ':': [[0,1,0],[0,0,0],[0,1,0],[0,0,0]],
        }
        
        for i, char in enumerate(text.upper()):
            if char in char_map:
                pixels = char_map[char]
                for cy in range(4):
                    for cx in range(3):
                        if pixels[cy][cx] == 1:
                            if 0 <= x + i*char_width + cx < GB_WIDTH and 0 <= y + cy < GB_HEIGHT:
                                surface.set_at((x + i*char_width + cx, y + cy), color)
    
    def run(self):
        clock = pygame.time.Clock()
        
        while True:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "playing":
                            self.state = "menu"
                    
                    if self.state == "playing":
                        if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                            self.player.jump()
                    
                    if self.state == "menu":
                        if event.key == pygame.K_RETURN:
                            self.state = "level_select"
                    
                    if self.state == "level_select":
                        if event.key == pygame.K_1 and self.level_unlocked[0]:
                            self.start_level(1)
                        elif event.key == pygame.K_2 and self.level_unlocked[1]:
                            self.start_level(2)
                        elif event.key == pygame.K_3 and self.level_unlocked[2]:
                            self.start_level(3)
                    
                    if self.state in ["game_over", "victory"]:
                        if event.key == pygame.K_RETURN:
                            self.state = "level_select"
            
            # Clear Game Boy surface
            self.gb_surface.fill(GB_LIGHTEST)
            
            # Game logic and drawing
            if self.state == "playing":
                keys = pygame.key.get_pressed()
                dx = 0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    dx = -PLAYER_SPEED
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    dx = PLAYER_SPEED
                
                self.player.move(dx, self.level.platforms, self.level.enemies, self.level.coins)
                
                # Move enemies
                for enemy in self.level.enemies:
                    enemy.move(self.level.platforms)
                
                # Camera scrolling
                if self.player.x - self.scroll_x > GB_WIDTH - SCROLL_THRESH:
                    self.scroll_x = self.player.x - (GB_WIDTH - SCROLL_THRESH)
                if self.player.x - self.scroll_x < SCROLL_THRESH:
                    self.scroll_x = self.player.x - SCROLL_THRESH
                
                self.scroll_x = max(0, min(self.scroll_x, self.level.level_width - GB_WIDTH))
                
                # Check victory
                if self.player.collision(self.level.goal):
                    self.level_unlocked[self.current_level - 1] = True
                    if self.current_level < 3:
                        self.level_unlocked[self.current_level] = True
                    self.state = "victory"
                
                # Check game over
                if not self.player.active:
                    self.state = "game_over"
                
                # Draw game
                self.draw_game()
                
            elif self.state == "menu":
                self.draw_menu()
            elif self.state == "level_select":
                self.draw_level_select()
            elif self.state == "game_over":
                self.draw_game()
                self.draw_game_over()
            elif self.state == "victory":
                self.draw_game()
                self.draw_victory()
            
            # Scale up and display
            scaled_surface = pygame.transform.scale(self.gb_surface, (WIDTH, HEIGHT))
            screen.blit(scaled_surface, (0, 0))
            
            pygame.display.flip()
            clock.tick(FPS)
    
    def draw_menu(self):
        # Title
        self.draw_text(self.gb_surface, "SUPER", 55, 30)
        self.draw_text(self.gb_surface, "MARIO LAND", 40, 40)
        
        # Instructions
        self.draw_text(self.gb_surface, "PRESS ENTER", 40, 80)
        
        # Draw Mario
        mario = [
            [0,0,1,1,1,0,0,0],
            [0,1,1,1,1,1,0,0],
            [0,1,2,2,2,1,0,0],
            [0,2,2,2,2,2,0,0],
            [0,0,1,1,1,0,0,0],
            [0,1,1,1,1,1,0,0],
            [0,1,0,0,0,1,0,0],
            [0,1,0,0,0,1,0,0]
        ]
        
        for y in range(8):
            for x in range(8):
                if mario[y][x] > 0:
                    color = GB_DARK if mario[y][x] == 1 else GB_DARKEST
                    self.gb_surface.set_at((76 + x, 100 + y), color)
    
    def draw_level_select(self):
        self.draw_text(self.gb_surface, "SELECT LEVEL", 35, 20)
        
        for i in range(3):
            y_pos = 50 + i * 25
            if self.level_unlocked[i]:
                self.draw_text(self.gb_surface, f"LEVEL {i+1}", 50, y_pos)
                self.draw_text(self.gb_surface, f"PRESS {i+1}", 50, y_pos + 10, GB_DARK)
            else:
                self.draw_text(self.gb_surface, "LOCKED", 50, y_pos, GB_LIGHT)
    
    def draw_game(self):
        # Draw platforms
        for platform in self.level.platforms:
            platform.draw(self.gb_surface, self.scroll_x)
        
        # Draw coins
        for coin in self.level.coins:
            coin.draw(self.gb_surface, self.scroll_x)
        
        # Draw enemies
        for enemy in self.level.enemies:
            enemy.draw(self.gb_surface, self.scroll_x)
        
        # Draw goal
        if self.level.goal:
            self.level.goal.draw(self.gb_surface, self.scroll_x)
        
        # Draw player
        self.player.draw(self.gb_surface, self.scroll_x)
        
        # Draw UI
        self.draw_text(self.gb_surface, f"L:{self.player.lives}", 5, 5)
        self.draw_text(self.gb_surface, f"C:{self.player.coins}", 40, 5)
        self.draw_text(self.gb_surface, f"LV:{self.current_level}", 80, 5)
    
    def draw_game_over(self):
        # Darken screen
        for y in range(GB_HEIGHT):
            for x in range(GB_WIDTH):
                if (x + y) % 2 == 0:
                    self.gb_surface.set_at((x, y), GB_DARK)
        
        self.draw_text(self.gb_surface, "GAME OVER", 50, 60)
        self.draw_text(self.gb_surface, "PRESS ENTER", 45, 80)
    
    def draw_victory(self):
        # Darken screen
        for y in range(GB_HEIGHT):
            for x in range(GB_WIDTH):
                if (x + y) % 2 == 0:
                    self.gb_surface.set_at((x, y), GB_LIGHT)
        
        self.draw_text(self.gb_surface, "LEVEL CLEAR", 45, 60)
        self.draw_text(self.gb_surface, f"COINS: {self.player.coins}", 50, 75)
        self.draw_text(self.gb_surface, "PRESS ENTER", 45, 90)

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()
