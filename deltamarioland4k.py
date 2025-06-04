import pygame
import sys
import math
import random
import numpy as np

# Initialize pygame and mixer for audio
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Game Boy screen dimensions and scale
GB_WIDTH, GB_HEIGHT = 160, 144
SCALE = 4  # Scale up for modern displays
WIDTH, HEIGHT = GB_WIDTH * SCALE, GB_HEIGHT * SCALE
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ULTRA! MARIO LAND - 60fps Tech Demo")

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

# Sound generation functions
def generate_square_wave(frequency, duration, sample_rate=22050, volume=0.3):
    """Generate a square wave (classic 8-bit sound)"""
    frames = int(duration * sample_rate)
    arr = np.zeros(frames)
    samples_per_cycle = sample_rate / frequency
    
    for i in range(frames):
        if (i % samples_per_cycle) < (samples_per_cycle / 2):
            arr[i] = volume
        else:
            arr[i] = -volume
    
    # Fade out to prevent clicks
    fade_frames = int(0.01 * sample_rate)
    for i in range(fade_frames):
        arr[-(i+1)] *= i / fade_frames
    
    return arr

def generate_noise(duration, sample_rate=22050, volume=0.2):
    """Generate white noise for explosion effects"""
    frames = int(duration * sample_rate)
    noise = np.random.normal(0, volume, frames)
    
    # Envelope
    envelope = np.exp(-np.linspace(0, 5, frames))
    return noise * envelope

def create_sound(wave_data, sample_rate=22050):
    """Convert wave data to pygame sound"""
    wave_data = np.array(wave_data * 32767, dtype=np.int16)
    stereo_data = np.zeros((len(wave_data), 2), dtype=np.int16)
    stereo_data[:, 0] = wave_data
    stereo_data[:, 1] = wave_data
    sound = pygame.sndarray.make_sound(stereo_data)
    return sound

# Create Game Boy style sound effects
class SoundEffects:
    def __init__(self):
        # Jump sound - rising pitch
        jump_wave = np.concatenate([
            generate_square_wave(200, 0.05),
            generate_square_wave(400, 0.05),
            generate_square_wave(600, 0.05)
        ])
        self.jump = create_sound(jump_wave)
        
        # Coin sound - two quick high notes
        coin_wave = np.concatenate([
            generate_square_wave(800, 0.1),
            generate_square_wave(1000, 0.1)
        ])
        self.coin = create_sound(coin_wave)
        
        # Stomp sound - quick low note
        stomp_wave = generate_square_wave(100, 0.1)
        self.stomp = create_sound(stomp_wave)
        
        # Damage sound - descending notes
        damage_wave = np.concatenate([
            generate_square_wave(400, 0.1),
            generate_square_wave(300, 0.1),
            generate_square_wave(200, 0.1)
        ])
        self.damage = create_sound(damage_wave)
        
        # Victory fanfare
        victory_wave = np.concatenate([
            generate_square_wave(523, 0.15),  # C
            generate_square_wave(659, 0.15),  # E
            generate_square_wave(784, 0.15),  # G
            generate_square_wave(1047, 0.3)   # High C
        ])
        self.victory = create_sound(victory_wave)
        
        # Game over sound
        gameover_wave = np.concatenate([
            generate_square_wave(300, 0.2),
            generate_square_wave(250, 0.2),
            generate_square_wave(200, 0.2),
            generate_square_wave(150, 0.4)
        ])
        self.gameover = create_sound(gameover_wave)
        
        # Menu select
        select_wave = generate_square_wave(600, 0.05)
        self.select = create_sound(select_wave)

# Initialize sound effects
sounds = SoundEffects()

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
        self.power_up = False  # Tech demo feature
        self.dying = False
        self.death_timer = 0
        
    def move(self, dx, platforms, enemies, coins):
        if not self.active:
            return
        
        # If dying, only update death animation
        if self.dying:
            self.death_timer += 1
            self.vel_y += GRAVITY * 0.5  # Slower fall when dying
            self.y += self.vel_y
            
            # Spin effect
            self.animation_frame += 0.5
            
            # After death animation, set inactive
            if self.death_timer > 60 or self.y > GB_HEIGHT + 20:
                self.active = False
            return
            
        # Horizontal movement
        speed_mult = 1.5 if self.power_up else 1.0
        self.x += dx * speed_mult
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
                    sounds.stomp.play()
                elif self.invincible <= 0:
                    # Take damage
                    self.invincible = 60
                    self.lives -= 1
                    sounds.damage.play()
                    if self.lives <= 0:
                        self.dying = True
                        self.vel_y = -JUMP_STRENGTH * 0.5  # Small death hop
                        sounds.gameover.play()
        
        # Coin collection
        for coin in coins[:]:
            if self.collision(coin):
                coins.remove(coin)
                self.coins += 1
                sounds.coin.play()
                # Every 10 coins = power up
                if self.coins % 10 == 0:
                    self.power_up = True
        
        # Keep player in bounds - trigger death animation
        if self.y > GB_HEIGHT:
            if not self.dying:
                self.dying = True
                sounds.gameover.play()
    
    def collision(self, obj):
        return (self.x < obj.x + obj.width and
                self.x + self.width > obj.x and
                self.y < obj.y + obj.height and
                self.y + self.height > obj.y)
    
    def jump(self):
        if not self.jumping and not self.dying:
            jump_mult = 1.2 if self.power_up else 1.0
            self.vel_y = -JUMP_STRENGTH * jump_mult
            self.jumping = True
            sounds.jump.play()
    
    def draw(self, surface, scroll_x):
        if not self.active and not self.dying:
            return
            
        if self.invincible > 0 and not self.dying:
            if self.invincible % 6 < 3:
                return
            self.invincible -= 1
        
        x_pos = int(self.x - scroll_x)
        y_pos = int(self.y)
        
        # Death animation - Mario flips upside down
        if self.dying:
            # Upside down Mario sprite
            mario_death = [
                [0,1,0,0,0,1,0,0],
                [0,1,0,0,0,1,0,0],
                [0,1,1,1,1,1,0,0],
                [0,0,1,1,1,0,0,0],
                [0,2,2,2,2,2,0,0],
                [0,1,2,2,2,1,0,0],
                [0,1,1,1,1,1,0,0],
                [0,0,1,1,1,0,0,0]
            ]
            
            # Draw death sprite with rotation effect
            angle = (self.death_timer * 10) % 360
            for y in range(8):
                for x in range(8):
                    if mario_death[y][x] > 0:
                        color = GB_DARK if mario_death[y][x] == 1 else GB_DARKEST
                        # Add some rotation offset based on death timer
                        draw_x = x_pos + x + int(math.sin(angle * 0.1) * 2)
                        draw_y = y_pos + y
                        if 0 <= draw_x < GB_WIDTH and 0 <= draw_y < GB_HEIGHT:
                            surface.set_at((draw_x, draw_y), color)
            return
        
        # Normal Mario sprite (8x8 pixels)
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
        
        # Draw Mario (with power-up glow effect)
        for y in range(8):
            for x in range(8):
                if pixels[y][x] > 0:
                    if pixels[y][x] == 1:
                        color = GB_DARK if not self.power_up else GB_DARKEST
                    else:
                        color = GB_DARKEST
                    if 0 <= x_pos + x < GB_WIDTH and 0 <= y_pos + y < GB_HEIGHT:
                        surface.set_at((x_pos + x, y_pos + y), color)
                        
        # Power-up sparkle effect
        if self.power_up and random.random() < 0.3:
            spark_x = x_pos + random.randint(-2, 9)
            spark_y = y_pos + random.randint(-2, 9)
            if 0 <= spark_x < GB_WIDTH and 0 <= spark_y < GB_HEIGHT:
                surface.set_at((spark_x, spark_y), GB_LIGHT)

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
    def __init__(self, x, y, enemy_type=0):
        self.x = x
        self.y = y
        self.width = 8
        self.height = 8
        self.direction = -1
        self.speed = 0.5 + (enemy_type * 0.2)
        self.active = True
        self.animation_frame = 0
        self.enemy_type = enemy_type
    
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
        
        if self.enemy_type == 0:
            # Goomba sprite (8x8)
            sprite = [
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
                sprite[7] = [1,0,1,0,0,1,0,1]
        else:
            # Flying enemy sprite
            sprite = [
                [0,1,0,0,0,0,1,0],
                [0,0,1,0,0,1,0,0],
                [1,1,1,1,1,1,1,1],
                [1,0,1,1,1,1,0,1],
                [1,1,1,0,0,1,1,1],
                [0,1,1,1,1,1,1,0],
                [0,0,1,0,0,1,0,0],
                [0,0,0,1,1,0,0,0]
            ]
            
            # Flap wings
            if int(self.animation_frame) == 1:
                sprite[2] = [1,0,1,1,1,1,0,1]
        
        # Draw enemy
        for y in range(8):
            for x in range(8):
                if sprite[y][x] == 1:
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
        self.animation = 0
    
    def draw(self, surface, scroll_x):
        x_pos = int(self.x - scroll_x)
        y_pos = int(self.y)
        
        self.animation += 0.1
        
        # Draw flag pole
        for y in range(32):
            if 0 <= x_pos + 7 < GB_WIDTH and 0 <= y_pos + y < GB_HEIGHT:
                surface.set_at((x_pos + 7, y_pos + y), GB_DARKEST)
                surface.set_at((x_pos + 8, y_pos + y), GB_DARKEST)
        
        # Animated flag
        wave = math.sin(self.animation) * 2
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
                    fx = x_pos + x + 9 + int(wave * (1 - y/5))
                    if 0 <= fx < GB_WIDTH and 0 <= y_pos + y + 5 < GB_HEIGHT:
                        surface.set_at((fx, y_pos + y + 5), GB_DARK)

class Level:
    def __init__(self, level_num):
        self.level_num = level_num
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.goal = None
        self.level_width = 640 + (level_num * 160)  # Levels get longer
        self.player_start = (20, 100)
        
        self.create_level(level_num)
    
    def create_level(self, num):
        # Ground with gaps
        gap_freq = max(1, 6 - num)  # More gaps in later levels
        for x in range(0, self.level_width, 16):
            if x % (gap_freq * 16) != 0 or x < 32:
                self.platforms.append(Platform(x, GB_HEIGHT - 16, 16, 16))
        
        if num == 1:
            # Level 1 - Introduction
            self.platforms.append(Platform(80, 100, 32, 8))
            self.platforms.append(Platform(140, 80, 24, 8))
            self.platforms.append(Platform(200, 100, 40, 8))
            self.platforms.append(Platform(280, 90, 32, 8))
            
            self.enemies.append(Enemy(100, 92, 0))
            self.enemies.append(Enemy(220, 92, 0))
            
            for i in range(5):
                self.coins.append(Coin(80 + i * 40, 65))
            
        elif num == 2:
            # Level 2 - Vertical challenge
            for i in range(8):
                y = 110 - (i % 3) * 20
                self.platforms.append(Platform(60 + i * 45, y, 30, 8))
                if i % 2 == 0:
                    self.enemies.append(Enemy(65 + i * 45, y - 8, 0))
            
            for i in range(10):
                self.coins.append(Coin(70 + i * 35, 50 + (i % 3) * 20))
                
        elif num == 3:
            # Level 3 - Enemy gauntlet
            for i in range(10):
                self.platforms.append(Platform(50 + i * 50, 100 - (i % 2) * 30, 35, 8))
                self.enemies.append(Enemy(55 + i * 50, 92 - (i % 2) * 30, i % 2))
            
            for i in range(15):
                self.coins.append(Coin(60 + i * 30, 40 + (i % 4) * 15))
        
        elif num == 4:
            # Level 4 - Precision platforming
            for i in range(12):
                width = 20 + (i % 3) * 5
                self.platforms.append(Platform(40 + i * 55, 120 - i * 3, width, 8))
                if i % 3 == 0:
                    self.enemies.append(Enemy(45 + i * 55, 112 - i * 3, 1))
            
            # Bonus coins in hard to reach places
            for i in range(20):
                self.coins.append(Coin(50 + i * 35, 30 + math.sin(i * 0.5) * 20))
                
        elif num == 5:
            # Level 5 - Ultimate challenge
            # Moving platform simulation (static but positioned like jumps)
            for i in range(15):
                x = 40 + i * 60
                y = 100 + math.sin(i * 0.8) * 30
                self.platforms.append(Platform(x, int(y), 25, 8))
                
                # Mixed enemy types
                enemy_type = 1 if i % 3 == 0 else 0
                self.enemies.append(Enemy(x + 5, int(y) - 8, enemy_type))
            
            # Coin spiral
            for i in range(30):
                angle = i * 0.3
                x = 300 + math.cos(angle) * (50 + i * 2)
                y = 70 + math.sin(angle) * 20
                self.coins.append(Coin(int(x), int(y)))
        
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
        self.level_unlocked = [True, False, False, False, False]
        self.frame_count = 0
        self.show_fps = True
        self.clock = pygame.time.Clock()
        
    def start_level(self, level_num):
        self.current_level = level_num
        self.level = Level(level_num)
        self.player = Player(*self.level.player_start)
        self.player.dying = False
        self.player.death_timer = 0
        self.scroll_x = 0
        self.state = "playing"
        sounds.select.play()
    
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
            '4': [[1,0,1],[1,0,1],[1,1,1],[0,0,1]],
            '5': [[1,1,1],[1,0,0],[0,1,1],[1,1,0]],
            '6': [[1,1,1],[1,0,0],[1,1,1],[1,1,1]],
            ' ': [[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
            ':': [[0,1,0],[0,0,0],[0,1,0],[0,0,0]],
            '!': [[0,1,0],[0,1,0],[0,0,0],[0,1,0]],
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
                    
                    if event.key == pygame.K_F1:
                        self.show_fps = not self.show_fps
                    
                    if self.state == "playing":
                        if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                            self.player.jump()
                    
                    if self.state == "menu":
                        if event.key == pygame.K_RETURN:
                            self.state = "level_select"
                            sounds.select.play()
                    
                    if self.state == "level_select":
                        if event.key == pygame.K_1 and self.level_unlocked[0]:
                            self.start_level(1)
                        elif event.key == pygame.K_2 and self.level_unlocked[1]:
                            self.start_level(2)
                        elif event.key == pygame.K_3 and self.level_unlocked[2]:
                            self.start_level(3)
                        elif event.key == pygame.K_4 and self.level_unlocked[3]:
                            self.start_level(4)
                        elif event.key == pygame.K_5 and self.level_unlocked[4]:
                            self.start_level(5)
                    
                    if self.state in ["game_over", "victory"]:
                        if event.key == pygame.K_RETURN:
                            self.state = "level_select"
                            sounds.select.play()
            
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
                    if self.current_level < 5:
                        self.level_unlocked[self.current_level] = True
                    self.state = "victory"
                    sounds.victory.play()
                
                # Check game over
                if not self.player.active and not self.player.dying:
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
            
            # Draw FPS counter if enabled
            if self.show_fps:
                fps = int(self.clock.get_fps())
                self.draw_text(self.gb_surface, f"{fps}FPS", GB_WIDTH - 28, 5, GB_DARK)
            
            # Scale up and display
            scaled_surface = pygame.transform.scale(self.gb_surface, (WIDTH, HEIGHT))
            screen.blit(scaled_surface, (0, 0))
            
            pygame.display.flip()
            self.clock.tick(FPS)
            self.frame_count += 1
    
    def draw_menu(self):
        # Animated title
        wave = math.sin(self.frame_count * 0.05) * 5
        
        # Title with effects
        self.draw_text(self.gb_surface, "ULTRA!", 50, 20 + int(wave))
        self.draw_text(self.gb_surface, "MARIO LAND", 35, 35)
        self.draw_text(self.gb_surface, "60FPS TECH DEMO", 25, 50, GB_DARK)
        
        # Instructions
        pulse = abs(math.sin(self.frame_count * 0.03))
        if pulse > 0.5:
            self.draw_text(self.gb_surface, "PRESS ENTER", 38, 90)
        
        # Animated Mario
        mario_y = 100 + math.sin(self.frame_count * 0.1) * 3
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
                    self.gb_surface.set_at((76 + x, int(mario_y) + y), color)
        
        # Tech demo info
        self.draw_text(self.gb_surface, "F1: TOGGLE FPS", 30, 125, GB_DARK)
    
    def draw_level_select(self):
        self.draw_text(self.gb_surface, "SELECT LEVEL", 35, 10)
        
        for i in range(5):
            y_pos = 30 + i * 20
            if self.level_unlocked[i]:
                # Highlight effect on unlocked levels
                if (self.frame_count // 10) % 5 == i:
                    color = GB_DARKEST
                else:
                    color = GB_DARK
                    
                self.draw_text(self.gb_surface, f"LEVEL {i+1}", 45, y_pos, color)
                self.draw_text(self.gb_surface, f"PRESS {i+1}", 45, y_pos + 8, GB_DARK)
            else:
                self.draw_text(self.gb_surface, "LOCKED", 45, y_pos, GB_LIGHT)
    
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
        
        # Draw UI with power-up indicator
        self.draw_text(self.gb_surface, f"L:{self.player.lives}", 5, 5)
        self.draw_text(self.gb_surface, f"C:{self.player.coins}", 35, 5)
        self.draw_text(self.gb_surface, f"LV:{self.current_level}", 70, 5)
        
        if self.player.power_up:
            self.draw_text(self.gb_surface, "POWER!", 100, 5, GB_DARKEST)
    
    def draw_game_over(self):
        # Darken screen with pattern
        for y in range(GB_HEIGHT):
            for x in range(GB_WIDTH):
                if (x + y) % 2 == 0:
                    self.gb_surface.set_at((x, y), GB_DARK)
        
        self.draw_text(self.gb_surface, "GAME OVER", 45, 60)
        self.draw_text(self.gb_surface, "PRESS ENTER", 40, 80)
    
    def draw_victory(self):
        # Victory animation
        for y in range(GB_HEIGHT):
            for x in range(GB_WIDTH):
                if (x + y + self.frame_count // 2) % 3 == 0:
                    self.gb_surface.set_at((x, y), GB_LIGHT)
        
        self.draw_text(self.gb_surface, "LEVEL CLEAR!", 40, 50)
        self.draw_text(self.gb_surface, f"COINS: {self.player.coins}", 45, 70)
        
        if self.current_level == 5:
            self.draw_text(self.gb_surface, "GAME COMPLETE!", 35, 90)
            self.draw_text(self.gb_surface, "AMAZING!", 50, 100)
        else:
            self.draw_text(self.gb_surface, "PRESS ENTER", 40, 90)

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()
