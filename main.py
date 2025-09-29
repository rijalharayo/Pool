import pygame
import sys
import enum
import math
import numpy as np
import random

from pygame import MOUSEBUTTONDOWN

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
FPS = 60
WIDTH, HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
FRICTION = 0.98
MAX_BALL_SPEED = 30
MIN_BALL_SPEED = 5

# Images and sprites
sky_image = pygame.image.load("img/sky.png")
sky_image = pygame.transform.scale(sky_image, (2500, 1000))

ground_image = pygame.image.load("img/grass.png")
button_sprite = pygame.image.load("img/button.png")

# Sound effects
wall_hit_sound = pygame.mixer.Sound("sounds/wall_hit.wav")
ball_hits_ball_sound = pygame.mixer.Sound("sounds/ball_hits_ball.wav")
white_ball_hit_sound = pygame.mixer.Sound("sounds/white_ball_hit.wav")

# Text font
main_font = "fonts/main_font.ttf"

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

class Team(enum.Enum):
    RED = Color.RED
    BLUE = Color.BLUE

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

class Hole(Component):
    def __init__(self, x, y, radius):
        super(Hole, self).__init__(x, y)
        self.radius = radius

    def draw(self, surface):
        pygame.draw.circle(surface, Color.BLACK.value, (self.x, self.y), self.radius)

    def check_ball_in_hole(self, ball):
        dx = self.x - ball.x
        dy = self.y - ball.y
        d = math.hypot(dx, dy)
        return d < self.radius + ball.radius

class Ball(Component):
    def __init__(self, x, y, radius, color):
        super(Ball, self).__init__(x, y)
        self.radius = radius
        self.color = color
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.theta = 0.0
        self.vel_main = 0.0
        self.mass = 0.2 #kg
        self.moving = False

    def draw(self, surface):
        pygame.draw.circle(surface, Color.BLACK.value, (self.x, self.y), self.radius + 10)
        pygame.draw.circle(surface, self.color.value, (int(self.x), int(self.y)), self.radius)

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
        # Extra hitbox
        hitbox_extra = 10
        return math.hypot(dx, dy) < self.radius + ball2.radius + hitbox_extra

    # Returns the tangent point/collision point
    def get_collision_point(self, ball2):
        phi = math.atan2(ball2.y - self.y, ball2.x - self.x)
        return self.x + self.radius * math.cos(phi), self.y + self.radius * math.sin(phi)

    # Elastic ball collisions
    def collide(self, ball2):
        # Push balls apart first
        Ball.displace_overlap(self, ball2)

        # Initial velocities
        initial_v1 = np.array([self.vel_x, self.vel_y])
        initial_v2 = np.array([ball2.vel_x, ball2.vel_y])

        impact_vector = np.array([ball2.x - self.x, ball2.y - self.y])
        impact_mag = np.linalg.norm(impact_vector)
        if impact_mag == 0:
            return  # avoid divide-by-zero

        relative_velocity = initial_v2 - initial_v1
        numerator = relative_velocity.dot(impact_vector) * impact_vector
        denominator = impact_mag ** 2

        final_velocity1 = initial_v1 + (numerator / denominator)
        final_velocity2 = initial_v2 + (-numerator / denominator)

        # Assign velocities from your formula
        self.vel_x, self.vel_y = final_velocity1
        ball2.vel_x, ball2.vel_y = final_velocity2

        # Fixes the final velocities to account for the tangent vector/line
        # Compute normal and tangent unit vectors
        nx, ny = impact_vector / impact_mag
        tx, ty = -ny, nx

        # Project new velocities onto normal/tangent
        v1n = self.vel_x * nx + self.vel_y * ny
        v1t = self.vel_x * tx + self.vel_y * ty
        v2n = ball2.vel_x * nx + ball2.vel_y * ny
        v2t = ball2.vel_x * tx + ball2.vel_y * ty

        # Recombine to get final 2D velocities
        self.vel_x = v1n * nx + v1t * tx
        self.vel_y = v1n * ny + v1t * ty
        ball2.vel_x = v2n * nx + v2t * tx
        ball2.vel_y = v2n * ny + v2t * ty

        # Both balls are moving
        self.moving = True
        ball2.moving = True

        self.update()

        # Total kinetic energy; Before and After
        #kinA = (0.5 * self.mass * np.linalg.norm(final_velocity1)) + (0.5 * ball2.mass * np.linalg.norm(final_velocity2))
        #kinB = (0.5 * self.mass * np.linalg.norm(initial_v1)) + (0.5 * ball2.mass * np.linalg.norm(initial_v2))

        # The kinetic energy is conserved
        #print(kinA, kinB)

    # Displaces the balls on overlap
    @staticmethod
    def displace_overlap(ball1, ball2):
        dx = ball1.x - ball2.x
        dy = ball1.y - ball2.y
        d = math.hypot(dx, dy)
        overlap = ball1.radius + ball2.radius - d

        if overlap > 0:
            # Normalized vector components
            nx = dx / d
            ny = dy / d

            ball1.x += (overlap / 2) * nx
            ball1.y += (overlap / 2) * ny

            ball2.x -= (overlap / 2) * nx
            ball2.y -= (overlap / 2) * ny

        return None

class Player(Ball):
    def __init__(self, x, y, radius):
        super(Player, self).__init__(x, y, radius, Color.WHITE)

    def draw_direction(self, surface):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Rotates the mouse position by 180 deg
        line_pos = (2 * self.x - mouse_x, 2 * self.y - mouse_y)
        pygame.draw.line(surface, Color.BLACK.value, self.pos, line_pos, 3)

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

class Text(Component):
    def __init__(self, x, y, text, size):
        super(Text, self).__init__(x, y)
        self.text = text
        self.size = size
        self.font = pygame.font.Font(main_font, size)
        self.custom_font = self.font.render(self.text, True, Color.BLACK.value)

    def draw(self, surface):
        surface.blit(self.custom_font, (self.x, self.y))

    def update_text(self, new_text):
        self.text = new_text
        self.custom_font = self.font.render(self.text, True, Color.BLACK.value)

class Button(Component):
    def __init__(self, x, y, width, height, text: Text):
        super(Button, self).__init__(x, y)
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text.custom_font
        text_rect = self.text.get_rect()
        self.text_pos = (x + (width - text_rect.width)//2, y + 5 + (height - text_rect.height)//2)
        self.sprite = pygame.transform.scale(button_sprite, (width, height))

    def draw(self, surface):
        surface.blit(self.sprite, (self.x, self.y))
        surface.blit(self.text, self.text_pos)

    def action(self):
        pass

# Game class to manage components
class Game:
    def __init__(self, player):
        self.player = player
        self.components = []
        self.pocketed_balls = []
        self.winner = None
        self.current_team = random.choice([Team.RED, Team.BLUE])
        self.score_red = 0
        self.score_blue = 0

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
                    if self.player.vel_main > MAX_BALL_SPEED:
                        self.player.vel_main = MAX_BALL_SPEED
                    elif self.player.vel_main < MIN_BALL_SPEED:
                        self.player.vel_main = MIN_BALL_SPEED

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

            for wall in WALLS:
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
                for ball in BALLS:
                    if ball.moving:
                        wall_collision = wall.check_collision(ball.x, ball.y, ball.radius)
                        # Returns [hasCollided, isCollisionVertical]
                        if wall_collision[0]:
                            if wall_collision[1]:
                                ball.vel_x = -ball.vel_x
                            else:
                                ball.vel_y = -ball.vel_y

                            wall_hit_sound.play()

            for i, ball in enumerate(BALLS):
                Ball.displace_overlap(ball, self.player)

                # Check collision with player
                if ball.check_ball_collision(self.player):
                    ball.collide(self.player)

                    if self.player.moving or ball:
                        ball_hits_ball_sound.play()

                # Check collision with other balls
                for j in range(i + 1, len(BALLS)):
                    ball2 = BALLS[j]
                    Ball.displace_overlap(ball, ball2)
                    if ball.check_ball_collision(ball2):
                        ball.collide(ball2)

                        if ball.moving or ball2.moving:
                            ball_hits_ball_sound.play()

                # Checks if any ball went inside the hole
                for hole in HOLES:
                    if hole.check_ball_in_hole(ball):
                        BALLS.remove(ball)
                        self.components.remove(ball)
                        self.pocketed_balls.append(ball)
                        if ball.color == Color.RED:
                            self.score_red += 1
                            TEXTS[0].update_text("Red: " + str(self.score_red))
                        else:
                            self.score_blue += 1
                            TEXTS[1].update_text("Blue: " + str(self.score_blue))

            # Shows the direction pointed
            if not self.player.moving:
                self.player.draw_direction(screen)

            if self.player.moving:
                self.player.update()

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

sub_steps = 4

# Game objects
BUTTONS = [
    Button(x = 5, y = 5, width = 150, height = 50, text = Text(text = "Reset", x = 0, y = 0, size = 40))
]
PLAYER = Player(x = 500, y = 400, radius = 15)
WALLS = [
    Wall(x = 40, y = 40, width = 60, height = 820),
    Wall(x = 100, y = 40, width = 1460, height = 60),
    Wall(x = 1500, y = 40, width = 60, height = 820),
    Wall(x = 100, y = 800, width = 1400, height = 60)
]
BALLS = [
    Ball(x = 700, y = 400, radius = 15, color = Color.BLUE),
    Ball(x = 770, y = 400, radius = 15, color = Color.BLUE),
    Ball(x = 840, y = 400, radius = 15, color = Color.BLUE),
    Ball(x = 910, y = 400, radius = 15, color = Color.BLUE),

    Ball(x = 700, y = 500, radius = 15, color = Color.RED),
    Ball(x = 770, y = 500, radius = 15, color = Color.RED),
    Ball(x = 840, y = 500, radius = 15, color = Color.RED),
    Ball(x = 910, y = 500, radius = 15, color = Color.RED)
]
HOLES = [
    Hole(x = 120, y = 120, radius = 40),
    Hole(x = 780, y = 120, radius = 40),
    Hole(x = 1480, y = 120, radius = 40),

    Hole(x = 120, y = 780, radius = 40),
    Hole(x = 780, y = 780, radius = 40),
    Hole(x = 1480, y = 780, radius = 40)
]
TEAMS = [Team.RED, Team.BLUE]
platforms = [
    Platform(x = 100, y = 100, width = 1400, height = 700)
]

# Create game
game = Game(PLAYER)

TEXTS = [
    Text(x = 1300, y = 50, text="Red: " + str(game.score_red), size = 55),
    Text(x = 1000, y = 50, text="Blue: " + str(game.score_blue), size = 55)
]

for platform in platforms:
    game.add_component(platform)

for hole in HOLES:
    game.add_component(hole)

for wall in WALLS:
    game.add_component(wall)

for ball in BALLS:
    game.add_component(ball)

for button in BUTTONS:
    game.add_component(button)

for text in TEXTS:
    game.add_component(text)

game.add_component(PLAYER)

# Run the game
game.run()