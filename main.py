import pygame
import sys
import enum
import math
import numpy as np

from pygame import MOUSEBUTTONDOWN

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
FPS = 60
WIDTH, HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
FRICTION = 0.98

# Background image
sky_image = pygame.image.load("img/sky.png")
sky_image = pygame.transform.scale(sky_image, (2500, 1000))

ground_image = pygame.image.load("img/grass.png")

wall_hit_sound = pygame.mixer.Sound("sounds/wall_hit.wav")
white_ball_hit_sound = pygame.mixer.Sound("sounds/white_ball_hit.wav");

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Pool")

# Clock
clock = pygame.time.Clock()

class Color(enum.Enum):
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (237, 17, 54)
    BLUE = (120, 166, 240)
    GREEN = (72, 110, 0)

# Base Component Class
class Component:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.pos = (self.x, self.y)

    def update(self):
        pass

    def draw(self, surface):
        pass

class Platform(Component):
    def __init__(self, x, y, width, height):
        super(Platform, self).__init__(x, y)
        self.width = width
        self.height = height
        self.sprite = pygame.transform.scale(ground_image, (width, height))

    def draw(self, surface):
        surface.blit(self.sprite, (self.x, self.y))

class Wall(Component):
    border_w = 10

    def __init__(self, x, y, width, height):
        super(Wall, self).__init__(x, y)
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x, y, self.width, self.height)

    def draw(self, surface):
        # Wall border ( Border width = 10 )
        pygame.draw.rect(surface, Color.BLACK.value, (self.x, self.y, self.width, self.height), self.border_w)
        pygame.draw.rect(surface, Color.GREEN.value, (self.x + self.border_w , self.y + self.border_w, self.width - 2 * self.border_w, self.height - 2 * self.border_w))

    # Checks if a ball has collided with a wall
    def check_collision(self, ball_x, ball_y, ball_radius):
        closest_x = max(self.rect.left, min(ball_x, self.rect.right))
        closest_y = max(self.rect.top, min(ball_y, self.rect.bottom))
        distance_x = ball_x - closest_x
        distance_y = ball_y - closest_y

        return [(distance_x ** 2 + distance_y ** 2) < ball_radius ** 2, abs(distance_x) > abs(distance_y)]

class Ball(Component):
    def __init__(self, x, y, radius, color):
        super(Ball, self).__init__(x, y)
        self.radius = radius
        self.color = color
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.theta = 0.0
        self.vel_main = 0.0
        self.moving = False

    def draw(self, surface):
        pygame.draw.circle(surface, Color.BLACK.value, (self.x, self.y), self.radius + 10)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

    # Updates the ball's position
    def update(self):
        if self.moving:
            self.x += self.vel_x
            self.y += self.vel_y

            self.pos = (self.x, self.y)

            self.vel_x *= FRICTION
            self.vel_y *= FRICTION

            if abs(self.vel_x) < 0.01 and abs(self.vel_y) < 0.01:
                self.moving = False
                self.vel_main = 0.0
                self.vel_x = 0
                self.vel_y = 0
                self.theta = 0

    # Checks for collision between 2 balls
    def check_ball_collision(self, ball2):
        dx = self.x - ball2.x
        dy = self.y - ball2.y
        # Extends the hitbox a little
        hitbox_extra = 15

        return dx**2 + dy**2 < (self.radius + ball2.radius + hitbox_extra)**2 + hitbox_extra**2

    # Returns the tangent point/collision point
    def get_collision_point(self, ball2):
        phi = math.atan2(ball2.y - self.y, ball2.x - self.x)
        return self.x + self.radius * math.cos(phi), self.y + self.radius * math.sin(phi)

    def deflect(self, ball2):
        collision_point = self.get_collision_point(ball2)
        print(collision_point)

        # Two key vectors (Normal vector and movement vector)
        normal_vector = [collision_point[0] - self.x, collision_point[1] - self.y]
        normal_angle = math.atan2(normal_vector[1], normal_vector[0])
        movement_vector = [ball2.vel_x, ball2.vel_y]

        dot_product = np.dot(normal_vector, movement_vector)
        distance_product = math.hypot(normal_vector[0], normal_vector[1]) * math.hypot(movement_vector[0], movement_vector[1])
        cosine = dot_product / distance_product
        alpha = math.acos(cosine)

        ball2.theta = 2 * alpha
        ball2.set_existing_vector()

class Player(Ball):
    def __init__(self, x, y, radius):
        super(Player, self).__init__(x, y, radius, Color.WHITE.value)

    def draw_direction(self, surface):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Rotates the mouse position by 180 deg
        line_pos = (2 * self.x - mouse_x, 2 * self.y - mouse_y)
        pygame.draw.line(surface, Color.BLACK.value, self.pos, line_pos, 2)

        # Gets the slope of the line as an angle
        self.theta = math.atan2(line_pos[1] - self.y, line_pos[0] - self.x)
        # Gets the distance between the curser and player, and sets it as the main velocity
        self.vel_main = math.sqrt(math.hypot(mouse_x - self.x, mouse_y - self.y))

    def set_update_vector(self):
        # Gets the movement vector
        self.vel_y = self.vel_main * math.sin(self.theta)
        self.vel_x = self.vel_main * math.cos(self.theta)

    def set_existing_vector(self):
        # Gets the new movement vector from the existing one
        self.vel_x *= math.cos(self.theta)
        self.vel_y *= math.sin(self.theta)

# Game class to manage components
class Game:
    def __init__(self, player, walls, balls):
        self.player = player
        self.walls = walls
        self.balls = balls
        self.components = []

    def add_component(self, component):
        self.components.append(component)

    def run(self):
        running = True
        sky_image.convert(screen)
        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

                if event.type == MOUSEBUTTONDOWN and not self.player.moving:
                    # Changes the motion state
                    self.player.moving = True
                    self.player.set_update_vector()
                    white_ball_hit_sound.play()

            # Update components
            for comp in self.components:
                comp.update()

            # Draw everything
            screen.blit(sky_image, (0, 0))
            for comp in self.components:
                comp.draw(screen)

            for wall in self.walls:
                if self.player.moving:
                    wall_collision = wall.check_collision(self.player.x, self.player.y, self.player.radius)
                    # Returns [hasCollided, isCollisionVertical]
                    if wall_collision[0]:
                        if wall_collision[1]:
                            self.player.vel_x = -self.player.vel_x
                        else:
                            self.player.vel_y = -self.player.vel_y

                        wall_hit_sound.play()

                # Checks for collision with other balls
                for ball in self.balls:
                    if ball.moving:
                        wall_collision = wall.check_collision(ball.x, ball.y, ball.radius)
                        # Returns [hasCollided, isCollisionVertical]
                        if wall_collision[0]:
                            if wall_collision[1]:
                                ball.vel_x = -ball.vel_x
                            else:
                                ball.vel_y = -ball.vel_y

                            wall_hit_sound.play()

            for ball in self.balls:
                # Only returns a boolean
                ball_collision = ball.check_ball_collision(self.player)
                if ball_collision:
                    ball.deflect(self.player)

            # Shows the direction pointed
            if not self.player.moving:
                self.player.draw_direction(screen)

            if self.player.moving:
                self.player.update()

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

# Game objects
PLAYER = Player(x = 200, y = 500, radius = 15)
WALLS = [
    Wall(x = 40, y = 40, width = 60, height = 820),
    Wall(x = 100, y = 40, width = 1460, height = 60),
    Wall(x = 1500, y = 40, width = 60, height = 820),
    Wall(x = 100, y = 800, width = 1400, height = 60)
]
BALLS = [
    Ball(x = 500, y = 500, radius = 15, color = Color.BLUE.value)
]
platforms = [
    Platform(x = 100, y = 100, width = 1400, height = 700)
]

# Create game
game = Game(PLAYER, WALLS, BALLS)

for wall in WALLS:
    game.add_component(wall)

for platform in platforms:
    game.add_component(platform)

for ball in BALLS:
    game.add_component(ball)

game.add_component(PLAYER)

# Run the game
game.run()
