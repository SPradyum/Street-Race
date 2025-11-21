"""
Advanced Street Racer — Cartoon / Arcade style
Updated: Road scrolling fixed (forward motion) + UI enhancements (cartoon look)
Single-file: street_racer.py
Requires: pygame
Optional assets: ./assets/player.png, enemy1.png, enemy2.png, crash.wav, bg_music.mp3
"""

import pygame
import random
import math
import os
import sys
from pathlib import Path

# ========== Configuration ==========
FPS = 60
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 800
LANE_COUNT = 3
ROAD_EDGE_PADDING = 36
LANE_WIDTH = (WINDOW_WIDTH - 2 * ROAD_EDGE_PADDING) // LANE_COUNT
ASSETS_DIR = Path(__file__).with_name("assets")
HIGHSCORE_FILE = Path("racer_highscore.txt")

# Gameplay tuning
PLAYER_MAX_SPEED = 420        # px/s
PLAYER_ACCEL = 700            # px/s^2
PLAYER_FRICTION = 700         # px/s^2
ENEMY_BASE_SPEED = 220        # px/s
ENEMY_SPEED_INCREMENT = 14
SPAWN_BASE_INTERVAL = 1.05
SPAWN_DECREASE_PER_LEVEL = 0.05
LEVEL_UP_SCORE = 100

# ========== Helpers ==========
def load_image(name):
    p = ASSETS_DIR / name
    if p.exists():
        try:
            img = pygame.image.load(str(p)).convert_alpha()
            return img
        except Exception:
            return None
    return None

def load_sound(name):
    p = ASSETS_DIR / name
    if p.exists():
        try:
            return pygame.mixer.Sound(str(p))
        except Exception:
            return None
    return None

def clamp(v, a, b):
    return max(a, min(b, v))

# ========== Road & Visuals ==========
class Road:
    """Cartoon-style road with downward dashed lines (forward motion)."""
    def __init__(self, surface):
        self.surface = surface
        self.scroll = 0.0
        self.line_length = 44
        self.line_gap = 28
        self.bg_top = (135, 206, 250)     # sky blue
        self.bg_bottom = (255, 240, 230)  # light peach
        self.color_edge = (20, 20, 30)    # borders
        self.color_lane = (60, 60, 70)    # road mid tone
        self.color_dash = (255, 235, 120) # cheerful yellow dash
        self.road_noise = None

    def update(self, dy):
        # dy is positive to indicate forward motion; increase scroll so dashes move down
        self.scroll = (self.scroll + dy) % (self.line_length + self.line_gap)

    def draw(self):
        s = self.surface
        # sky gradient
        for y in range(WINDOW_HEIGHT):
            t = y / WINDOW_HEIGHT
            r = int(self.bg_top[0] * (1 - t) + self.bg_bottom[0] * t)
            g = int(self.bg_top[1] * (1 - t) + self.bg_bottom[1] * t)
            b = int(self.bg_top[2] * (1 - t) + self.bg_bottom[2] * t)
            s.fill((r, g, b), (0, y, WINDOW_WIDTH, 1))
        # Draw road area (rounded edges feel cartoonish)
        road_x = ROAD_EDGE_PADDING
        road_w = WINDOW_WIDTH - 2 * ROAD_EDGE_PADDING
        pygame.draw.rect(s, self.color_lane, (road_x, 0, road_w, WINDOW_HEIGHT), border_radius=12)
        # Road edges (bright)
        pygame.draw.rect(s, self.color_edge, (0, 0, ROAD_EDGE_PADDING, WINDOW_HEIGHT))
        pygame.draw.rect(s, self.color_edge, (WINDOW_WIDTH - ROAD_EDGE_PADDING, 0, ROAD_EDGE_PADDING, WINDOW_HEIGHT))
        # Draw outer decorative stripes (cartoon accent)
        left_stripe_rect = (road_x + 2, 0, 6, WINDOW_HEIGHT)
        right_stripe_rect = (road_x + road_w - 8, 0, 6, WINDOW_HEIGHT)
        pygame.draw.rect(s, (255, 150, 120), left_stripe_rect, border_radius=6)
        pygame.draw.rect(s, (255, 150, 120), right_stripe_rect, border_radius=6)
        # Dashed center lane markers (move downward -> use positive scroll)
        for lane in range(1, LANE_COUNT):
            x = road_x + lane * LANE_WIDTH
            dash_x = x - 6
            offset = self.scroll  # previously used -scroll; using positive value makes dashes move down
            y = -offset
            # draw rounded dashes for cartoon feel
            while y < WINDOW_HEIGHT:
                rrect = pygame.Rect(dash_x, int(y), 12, self.line_length)
                pygame.draw.rect(s, self.color_dash, rrect, border_radius=6)
                # small glow outline
                pygame.draw.rect(s, (255, 245, 200), rrect, width=1, border_radius=6)
                y += self.line_length + self.line_gap

# ========== Sprites ==========
class Car(pygame.sprite.Sprite):
    def __init__(self, x, y, width=50, height=100, color=(0, 150, 255), image=None):
        super().__init__()
        self.width = width
        self.height = height
        self.base_image = None
        if image:
            self.base_image = image
            ih, iw = image.get_height(), image.get_width()
            # scale preserving aspect ratio to fit width x height
            scale = min(width / iw, height / ih)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            self.base_image = pygame.transform.smoothscale(image, (new_w, new_h))
            self.image = self.base_image.copy()
            self.rect = self.image.get_rect(center=(x, y))
        else:
            self.image = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(self.image, color, (0, 0, width, height), border_radius=10)
            # front highlight and cartoon eyes (funny look)
            pygame.draw.rect(self.image, (255,255,255,70), (6, 8, width-12, height-30), border_radius=8)
            pygame.draw.circle(self.image, (255,255,255,120), (int(width*0.3), int(height*0.2)), 6)
            pygame.draw.circle(self.image, (255,255,255,120), (int(width*0.7), int(height*0.2)), 6)
            self.rect = self.image.get_rect(center=(x, y))
        self.x = float(self.rect.centerx)
        self.y = float(self.rect.centery)

    def update_rect(self):
        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)

class PlayerCar(Car):
    def __init__(self, lane_index, image=None):
        lane_x = RoadPosition.lane_center_x(lane_index)
        y = WINDOW_HEIGHT - 140
        super().__init__(lane_x, y, width=56, height=110, color=(12,200,120), image=image)
        self.speed = 0.0
        self.vx = 0.0
        self.lane_index = lane_index
        self.target_x = self.x
        self.shadow_surf = None

    def accelerate(self, dt):
        self.speed += PLAYER_ACCEL * dt
        self.speed = clamp(self.speed, 0, PLAYER_MAX_SPEED)

    def brake(self, dt):
        self.speed -= PLAYER_FRICTION * dt * 1.5
        if self.speed < 0:
            self.speed = 0

    def coast(self, dt):
        if self.speed > 0:
            self.speed -= PLAYER_FRICTION * dt
            if self.speed < 0:
                self.speed = 0

    def steer(self, direction, dt):
        # immediate shift but smoothed by interpolation in update
        shift = direction * 260 * dt
        self.target_x = clamp(self.x + shift, ROAD_EDGE_PADDING + self.width//2, WINDOW_WIDTH - ROAD_EDGE_PADDING - self.width//2)

    def move_to_lane(self, lane_index, dt):
        self.target_x = RoadPosition.lane_center_x(lane_index)
        self.lane_index = lane_index

    def update(self, dt, steering_dir=0):
        # smooth interpolation towards target_x (tween-like)
        diff = (self.target_x - self.x)
        self.x += diff * clamp(10 * dt, 0.0, 1.0)
        # apply tiny sway for cartoon feel
        sway = math.sin(pygame.time.get_ticks() * 0.004) * 0.2
        self.x += sway
        self.update_rect()

class EnemyCar(Car):
    def __init__(self, lane_index, y=-120, image=None, speed=ENEMY_BASE_SPEED):
        lane_x = RoadPosition.lane_center_x(lane_index)
        super().__init__(lane_x, y, width=52, height=98, color=(220,70,100), image=image)
        self.speed = speed
        self.lane_index = lane_index

    def update(self, dt):
        self.y += self.speed * dt
        self.update_rect()

class RoadPosition:
    @staticmethod
    def lane_center_x(lane_index):
        return ROAD_EDGE_PADDING + lane_index * LANE_WIDTH + LANE_WIDTH // 2

# ========== Game ==========
class StreetRacer:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Street Racer - Arcade")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.bigfont = pygame.font.SysFont("Arial", 36, bold=True)
        self.smallfont = pygame.font.SysFont("Arial", 14)

        # assets
        self.player_img = load_image("player.png")
        self.enemy_imgs = [load_image("enemy1.png"), load_image("enemy2.png")]
        self.bg_music = load_sound("bg_music.mp3")
        self.crash_sound = load_sound("crash.wav")

        self.road = Road(self.screen)
        self.all_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()

        middle_lane = LANE_COUNT // 2
        self.player = PlayerCar(middle_lane, image=self.player_img)
        self.all_sprites.add(self.player)

        self.spawn_timer = 0.0
        self.spawn_interval = SPAWN_BASE_INTERVAL
        self.score = 0
        self.level = 1
        self.running = False
        self.paused = False
        self.game_over = False
        self.highscore = self.load_highscore()

        # visual helpers
        self.show_instructions = True
        self.speedometer_value = 0.0
        self.shake_offset = (0, 0)

        # music
        if self.bg_music and pygame.mixer:
            try:
                pygame.mixer.music.load(str(ASSETS_DIR / "bg_music.mp3"))
                pygame.mixer.music.set_volume(0.22)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

    def load_highscore(self):
        try:
            if HIGHSCORE_FILE.exists():
                return int(HIGHSCORE_FILE.read_text())
        except Exception:
            pass
        return 0

    def save_highscore(self):
        try:
            HIGHSCORE_FILE.write_text(str(self.highscore))
        except Exception:
            pass

    def spawn_enemy(self):
        lane_idx = random.randrange(LANE_COUNT)
        y = -120
        speed = ENEMY_BASE_SPEED + (self.level - 1) * ENEMY_SPEED_INCREMENT + random.uniform(-30, 30)
        imgs = [i for i in self.enemy_imgs if i is not None]
        img = random.choice(imgs) if imgs else None
        enemy = EnemyCar(lane_idx, y=y, image=img, speed=speed)
        self.enemy_sprites.add(enemy)
        self.all_sprites.add(enemy)

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        turning = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            turning = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            turning = 1

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player.accelerate(dt)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.brake(dt)
        else:
            self.player.coast(dt)

        if turning != 0:
            self.player.steer(turning, dt)

        if keys[pygame.K_q]:
            new_lane = max(0, self.player.lane_index - 1)
            self.player.move_to_lane(new_lane, dt)
        elif keys[pygame.K_e]:
            new_lane = min(LANE_COUNT - 1, self.player.lane_index + 1)
            self.player.move_to_lane(new_lane, dt)

    def update(self, dt):
        if self.paused or self.game_over:
            return

        self.spawn_timer += dt
        effective_interval = max(0.45, SPAWN_BASE_INTERVAL - (self.level - 1) * SPAWN_DECREASE_PER_LEVEL)
        if self.spawn_timer >= effective_interval:
            self.spawn_timer = 0.0
            if random.random() < clamp(0.65 + (self.level * 0.03), 0.4, 1.0):
                self.spawn_enemy()

        for enemy in list(self.enemy_sprites):
            enemy.update(dt)
            if enemy.y - enemy.height // 2 > WINDOW_HEIGHT + 80:
                enemy.kill()
                self.score += 6

        # road scroll uses player's speed to simulate movement (positive -> dashes go down)
        scroll_speed = clamp(self.player.speed * 0.55 + 160, 120, 1000)
        self.road.update(scroll_speed * dt)

        self.player.update(dt)

        # motion streak: when speed is high, draw small streak lines later in draw phase

        # collision detection
        hit = pygame.sprite.spritecollideany(self.player, self.enemy_sprites)
        if hit:
            self.on_crash(hit)

        # level up
        if self.score // LEVEL_UP_SCORE + 1 > self.level:
            self.level += 1

    def on_crash(self, enemy):
        if self.crash_sound and pygame.mixer:
            try:
                pygame.mixer.Sound.play(self.crash_sound)
            except Exception:
                pass
        self.game_over = True
        self.running = False
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_highscore()

    def restart(self):
        for s in list(self.enemy_sprites):
            s.kill()
        self.enemy_sprites.empty()
        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.player)
        self.player.x = RoadPosition.lane_center_x(LANE_COUNT // 2)
        self.player.y = WINDOW_HEIGHT - 140
        self.player.speed = 0.0
        self.player.update_rect()
        self.spawn_timer = 0.0
        self.score = 0
        self.level = 1
        self.running = True
        self.paused = False
        self.game_over = False
        self.show_instructions = False

    def draw_speedometer(self):
        # digital style box bottom-right
        speed_kmh = int(self.player.speed * 0.1)  # arbitrary scale to look nice
        box_w, box_h = 120, 56
        x = WINDOW_WIDTH - box_w - 12
        y = WINDOW_HEIGHT - box_h - 40
        pygame.draw.rect(self.screen, (20, 20, 30), (x, y, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.screen, (255, 200, 60), (x+6, y+6, box_w-12, box_h-12), border_radius=6)
        txt = self.bigfont.render(f"{speed_kmh} km/h", True, (10,10,10))
        sub = self.font.render("SPEED", True, (10,10,10))
        self.screen.blit(txt, (x+10, y+6))
        self.screen.blit(sub, (x+10, y+34))

    def draw_motion_streaks(self):
        # draw horizontal faint streaks when speed high
        s = self.screen
        intensity = (self.player.speed / PLAYER_MAX_SPEED)
        if intensity < 0.35:
            return
        count = int(4 + intensity * 8)
        for i in range(count):
            y = WINDOW_HEIGHT * (0.15 + i * 0.08)
            alpha = int(10 + intensity * 30)
            streak = pygame.Surface((WINDOW_WIDTH, 2), pygame.SRCALPHA)
            streak.fill((255, 255, 255, alpha))
            s.blit(streak, (0, int(y + math.sin(pygame.time.get_ticks() * 0.002 + i) * 4)))

    def draw_player_shadow(self):
        # subtle oval shadow under player (cartoon)
        shadow_w = int(self.player.width * 1.6)
        shadow_h = int(self.player.height * 0.4)
        surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0,0,0,80), (0,0,shadow_w,shadow_h))
        sx = self.player.rect.centerx - shadow_w//2
        sy = self.player.rect.centery + self.player.height//2 - 12
        self.screen.blit(surf, (sx, sy))

    def draw_ui(self):
        hud_color = (250, 250, 250)
        score_surf = self.font.render(f"SCORE: {self.score}", True, hud_color)
        level_surf = self.font.render(f"LEVEL: {self.level}", True, hud_color)
        high_surf = self.font.render(f"HIGH: {self.highscore}", True, (255, 230, 90))
        self.screen.blit(score_surf, (12, 12))
        self.screen.blit(level_surf, (12, 36))
        self.screen.blit(high_surf, (WINDOW_WIDTH - 110, 12))

        controls = "←/A →/D steer  •  ↑/W accel  •  ↓/S brake  •  Q/E lane  •  P pause"
        ctrl_surf = self.smallfont.render(controls, True, (240,240,240))
        pygame.draw.rect(self.screen, (20,20,30), (8, WINDOW_HEIGHT - 28 - 8, WINDOW_WIDTH - 16, 28), border_radius=6)
        self.screen.blit(ctrl_surf, (14, WINDOW_HEIGHT - 26 - 4))

        if self.game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))
            go_surf = self.bigfont.render("BOOM!", True, (255, 80, 80))
            sub_surf = self.font.render("Press R to restart or Esc to quit", True, (240,240,240))
            self.screen.blit(go_surf, (WINDOW_WIDTH//2 - go_surf.get_width()//2, WINDOW_HEIGHT//2 - 40))
            self.screen.blit(sub_surf, (WINDOW_WIDTH//2 - sub_surf.get_width()//2, WINDOW_HEIGHT//2 + 8))
        elif self.show_instructions:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
            title = self.bigfont.render("Street Racer - Arcade", True, (255,255,255))
            sub = self.font.render("Avoid traffic. Survive. Score points.", True, (220,220,220))
            inst = self.font.render("Press SPACE to start", True, (200,200,200))
            self.screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 120))
            self.screen.blit(sub, (WINDOW_WIDTH//2 - sub.get_width()//2, 170))
            self.screen.blit(inst, (WINDOW_WIDTH//2 - inst.get_width()//2, 220))

    def draw_sprites(self):
        sprites = sorted(self.all_sprites, key=lambda s: s.rect.centery)
        for s in sprites:
            # draw shadow, then sprite for player
            if isinstance(s, PlayerCar):
                self.draw_player_shadow()
            self.screen.blit(s.image, s.rect)

    def run(self):
        dt = 0
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_highscore()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.save_highscore()
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_p:
                        if not self.game_over:
                            self.paused = not self.paused
                    if event.key == pygame.K_SPACE:
                        if self.show_instructions:
                            self.show_instructions = False
                            self.running = True
                            self.restart()
                    if event.key == pygame.K_r:
                        if self.game_over:
                            self.restart()

            if self.running and not self.paused and not self.game_over:
                self.handle_input(dt)
                self.update(dt)

            # draw
            self.road.draw()
            # motion streaks draw BEFORE sprites for a layered arcade effect
            self.draw_motion_streaks()
            self.draw_sprites()
            self.draw_ui()
            self.draw_speedometer()

            pygame.display.flip()

# ========== Entry point ==========
def main():
    if not ASSETS_DIR.exists():
        try:
            ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    game = StreetRacer()
    game.run()

if __name__ == "__main__":
    main()
